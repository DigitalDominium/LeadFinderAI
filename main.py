from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from services.google_maps import find_business_leads, GoogleMapsError
from services.ai_analyzer import analyze_lead_with_ai
from services.voice import transcribe_audio, text_to_speech, interpret_command
from services.exporter import export_leads_to_excel

app = FastAPI(title="Dominium LeadRadar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ──────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    location: str
    industry: str
    radius_km: float = 10.0
    count: int = 10

class AnalyzeRequest(BaseModel):
    leads: list[dict[str, Any]]
    target_service: str = "Warehousing, VAS, inventory management"
    model: str = "gpt-4.1-mini"

class ExportRequest(BaseModel):
    leads: list[dict[str, Any]]

class TTSRequest(BaseModel):
    text: str


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "online"}


@app.post("/api/search")
async def search_leads(req: SearchRequest):
    try:
        leads, formatted_location = find_business_leads(
            req.location, req.industry, req.radius_km, req.count
        )
        return {"leads": leads, "location": formatted_location, "count": len(leads)}
    except GoogleMapsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_leads(req: AnalyzeRequest):
    try:
        analyzed = []
        for lead in req.leads:
            result = analyze_lead_with_ai(lead, req.target_service, model=req.model)
            lead.update(result)
            analyzed.append(lead)
        return {"leads": analyzed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
async def export_leads(req: ExportRequest):
    try:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        export_leads_to_excel(req.leads, tmp_path)
        return FileResponse(
            path=str(tmp_path),
            filename="Dominium_LeadRadar_Export.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        text = transcribe_audio(audio_bytes, file.filename or "audio.webm")
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
async def tts(req: TTSRequest):
    try:
        audio_bytes = text_to_speech(req.text)
        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interpret")
async def interpret(req: dict):
    try:
        command_text = req.get("text", "")
        result = interpret_command(command_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Serve frontend ───────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
