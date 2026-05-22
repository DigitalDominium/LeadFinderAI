from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

from services.ai_analyzer import analyze_lead_with_ai
from services.database import (
    add_activity,
    create_campaign,
    delete_lead,
    duplicate_lookup,
    get_campaign,
    get_campaigns,
    get_dashboard,
    get_due_followups,
    get_lead,
    get_leads,
    init_db,
    save_imported_leads,
    save_lead,
    update_lead,
)
from services.exporter import export_leads_to_excel
from services.google_maps import GoogleMapsError, find_business_leads
from services.outreach import generate_outreach_asset, generate_proposal_asset
from services.voice import interpret_command, text_to_speech, transcribe_audio
from services.website_scanner import scan_website


app = FastAPI(title="Dominium LeadRadar V2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    campaign_name: str = "New Lead Campaign"
    location: str
    industry: str
    radius_km: float = 10.0
    count: int = 10
    target_service: str = "Warehousing, VAS, inventory management"
    assigned_to: str = ""
    save_to_crm: bool = True


class AnalyzeRequest(BaseModel):
    lead_ids: list[int] | None = None
    campaign_id: int | None = None
    leads: list[dict[str, Any]] | None = None
    target_service: str = "Warehousing, VAS, inventory management"
    model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    save_results: bool = True


class LeadUpdateRequest(BaseModel):
    sales_stage: str | None = None
    assigned_to: str | None = None
    next_follow_up_date: str | None = None
    last_contacted_date: str | None = None
    estimated_potential: str | None = None
    service_fit: str | None = None
    notes: str | None = None
    decision_maker_name: str | None = None
    decision_maker_title: str | None = None
    decision_maker_email: str | None = None
    decision_maker_phone: str | None = None
    linkedin_url: str | None = None
    priority: str | None = None


class CampaignRequest(BaseModel):
    name: str
    location: str = ""
    industry: str = ""
    radius_km: float = 10.0
    target_service: str = "Warehousing, VAS, inventory management"
    owner: str = ""


class ExportRequest(BaseModel):
    campaign_id: int | None = None
    stage: str | None = None
    priority: str | None = None
    assigned_to: str | None = None


class OutreachRequest(BaseModel):
    asset_type: str = "cold_email"
    tone: str = "professional"
    model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))


class ProposalRequest(BaseModel):
    model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))


class WebsiteScanRequest(BaseModel):
    lead_id: int | None = None
    url: str | None = None


class TTSRequest(BaseModel):
    text: str


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "online", "app": "Dominium LeadRadar V2"}


@app.post("/api/campaigns")
def api_create_campaign(req: CampaignRequest) -> dict[str, Any]:
    campaign_id = create_campaign(req.model_dump())
    return {"campaign_id": campaign_id, "campaign": get_campaign(campaign_id)}


@app.get("/api/campaigns")
def api_campaigns() -> dict[str, Any]:
    return {"campaigns": get_campaigns()}


@app.post("/api/search")
def search_leads(req: SearchRequest) -> dict[str, Any]:
    try:
        found, formatted_location = find_business_leads(req.location, req.industry, req.radius_km, req.count)
        campaign_id = None
        saved: list[dict[str, Any]] = []

        if req.save_to_crm:
            campaign_id = create_campaign(
                {
                    "name": req.campaign_name,
                    "location": formatted_location,
                    "industry": req.industry,
                    "radius_km": req.radius_km,
                    "target_service": req.target_service,
                    "owner": req.assigned_to,
                }
            )
            for lead in found:
                duplicate = duplicate_lookup(lead)
                lead.update(
                    {
                        "campaign_id": campaign_id,
                        "assigned_to": req.assigned_to,
                        "source": "Google Places",
                        "sales_stage": "New",
                        "service_fit": req.target_service,
                        "duplicate_of": duplicate.get("id") if duplicate else None,
                    }
                )
                lead_id = save_lead(lead)
                saved_lead = get_lead(lead_id)
                saved.append(saved_lead)
        else:
            saved = found

        return {
            "campaign_id": campaign_id,
            "location": formatted_location,
            "count": len(saved),
            "leads": saved,
        }
    except GoogleMapsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/analyze")
def analyze_leads(req: AnalyzeRequest) -> dict[str, Any]:
    try:
        if req.leads is not None:
            input_leads = req.leads
        elif req.lead_ids:
            input_leads = [get_lead(lead_id) for lead_id in req.lead_ids]
        elif req.campaign_id:
            input_leads = get_leads(campaign_id=req.campaign_id)
        else:
            raise HTTPException(status_code=400, detail="Provide leads, lead_ids, or campaign_id.")

        analyzed: list[dict[str, Any]] = []
        for lead in input_leads:
            if not lead:
                continue
            analysis = analyze_lead_with_ai(lead, req.target_service, model=req.model)
            lead.update(analysis)
            if req.save_results and lead.get("id"):
                update_lead(int(lead["id"]), analysis)
                add_activity(int(lead["id"]), "AI Analysis", "Lead analyzed and scoring updated.")
                analyzed.append(get_lead(int(lead["id"])))
            else:
                analyzed.append(lead)

        return {"count": len(analyzed), "leads": analyzed}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/leads/{lead_id}/analyze")
def analyze_one_lead(lead_id: int, req: AnalyzeRequest) -> dict[str, Any]:
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    analysis = analyze_lead_with_ai(lead, req.target_service, model=req.model)
    update_lead(lead_id, analysis)
    add_activity(lead_id, "AI Analysis", "Single lead analyzed.")
    return {"lead": get_lead(lead_id)}


@app.get("/api/leads")
def api_get_leads(
    campaign_id: int | None = None,
    stage: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    return {"leads": get_leads(campaign_id, stage, priority, assigned_to, query)}


@app.get("/api/leads/{lead_id}")
def api_get_lead(lead_id: int) -> dict[str, Any]:
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return {"lead": lead}


@app.put("/api/leads/{lead_id}")
def api_update_lead(lead_id: int, req: LeadUpdateRequest) -> dict[str, Any]:
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    update_lead(lead_id, changes)
    add_activity(lead_id, "Lead Updated", ", ".join(changes.keys()) or "Lead updated.")
    return {"lead": get_lead(lead_id)}


@app.delete("/api/leads/{lead_id}")
def api_delete_lead(lead_id: int) -> dict[str, Any]:
    delete_lead(lead_id)
    return {"status": "deleted"}


@app.get("/api/dashboard")
def api_dashboard() -> dict[str, Any]:
    return get_dashboard()


@app.get("/api/followups")
def api_followups(days: int = Query(7, ge=0, le=365)) -> dict[str, Any]:
    return {"leads": get_due_followups(days)}


@app.post("/api/leads/{lead_id}/outreach")
def api_outreach(lead_id: int, req: OutreachRequest) -> dict[str, Any]:
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    asset = generate_outreach_asset(lead, req.asset_type, req.tone, model=req.model)
    add_activity(lead_id, "Outreach Generated", f"{req.asset_type} generated.")
    return {"asset": asset}


@app.post("/api/leads/{lead_id}/proposal")
def api_proposal(lead_id: int, req: ProposalRequest) -> dict[str, Any]:
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    asset = generate_proposal_asset(lead, model=req.model)
    add_activity(lead_id, "Proposal Generated", "Proposal outline generated.")
    return {"proposal": asset}


@app.post("/api/website-scan")
def api_website_scan(req: WebsiteScanRequest) -> dict[str, Any]:
    try:
        url = req.url
        lead_id = req.lead_id
        if lead_id:
            lead = get_lead(lead_id)
            if not lead:
                raise HTTPException(status_code=404, detail="Lead not found.")
            url = lead.get("website") or url
        if not url:
            raise HTTPException(status_code=400, detail="No website URL provided.")

        summary = scan_website(url)
        if lead_id:
            update_lead(lead_id, {"website_summary": summary.get("summary", "")})
            add_activity(lead_id, "Website Scan", "Website summary updated.")
        return summary
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/linkedin-search")
def api_linkedin_search(company: str, title: str = "Logistics Manager") -> dict[str, str]:
    import urllib.parse

    company_token = company.split()[0] if company else ""
    keywords = urllib.parse.quote(f'{company_token} "{title}"')
    return {
        "people_search_url": f"https://www.linkedin.com/search/results/people/?keywords={keywords}",
        "google_search_url": f"https://www.google.com/search?q={keywords}+site%3Alinkedin.com%2Fin",
    }


@app.post("/api/export")
def api_export(req: ExportRequest):
    try:
        leads = get_leads(req.campaign_id, req.stage, req.priority, req.assigned_to, None)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        export_leads_to_excel(leads, tmp_path)
        return FileResponse(
            path=str(tmp_path),
            filename="Dominium_LeadRadar_V2_Export.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/import-excel")
async def api_import_excel(file: UploadFile = File(...), campaign_id: int | None = None):
    try:
        import pandas as pd

        raw = await file.read()
        df = pd.read_excel(io.BytesIO(raw))
        records = df.fillna("").to_dict(orient="records")
        inserted = save_imported_leads(records, campaign_id=campaign_id)
        return {"inserted": inserted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        return {"text": transcribe_audio(audio_bytes, file.filename or "audio.webm")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/tts")
def tts(req: TTSRequest):
    try:
        return StreamingResponse(io.BytesIO(text_to_speech(req.text)), media_type="audio/mpeg")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/interpret")
def interpret(req: dict):
    try:
        return interpret_command(req.get("text", ""))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
