from __future__ import annotations

import os
from typing import Any

from openai import OpenAI


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in Render environment variables.")
    return OpenAI(api_key=api_key)


def lead_context(lead: dict[str, Any]) -> str:
    return f"""
Company: {lead.get('name', '')}
Address: {lead.get('address', '')}
Website: {lead.get('website', '')}
Phone: {lead.get('phone', '')}
Priority: {lead.get('priority', '')}
Lead score: {lead.get('lead_score', '')}
Suggested service: {lead.get('suggested_service', '') or lead.get('service_fit', '')}
Potential pain points: {lead.get('possible_pain_points', '')}
Reasoning: {lead.get('reasoning_summary', '')}
Decision maker: {lead.get('decision_maker_name', '')} {lead.get('decision_maker_title', '')}
Notes: {lead.get('notes', '')}
"""


def generate_outreach_asset(
    lead: dict[str, Any],
    asset_type: str = "cold_email",
    tone: str = "professional",
    model: str | None = None,
) -> dict[str, str]:
    model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = get_client()

    asset_instructions = {
        "cold_email": "Create a concise cold email with subject and body.",
        "follow_up_email": "Create a polite follow-up email after no response.",
        "linkedin_message": "Create a LinkedIn connection message under 300 characters.",
        "call_script": "Create a cold call opening script with 4 short lines.",
        "whatsapp_message": "Create a short WhatsApp-style B2B outreach message.",
        "meeting_request": "Create a meeting request message with a clear reason and proposed agenda.",
    }
    instruction = asset_instructions.get(asset_type, asset_instructions["cold_email"])

    prompt = f"""
You are helping a contract logistics sales team prepare outreach.

Tone: {tone}
Asset type: {asset_type}
Instruction: {instruction}

Lead details:
{lead_context(lead)}

Return a clear ready-to-use message. Keep it practical and professional.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You write concise B2B logistics sales outreach."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=700,
        temperature=0.35,
    )
    return {"asset_type": asset_type, "content": (response.choices[0].message.content or "").strip()}


def generate_proposal_asset(lead: dict[str, Any], model: str | None = None) -> dict[str, str]:
    model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = get_client()

    prompt = f"""
Create a management-ready mini proposal outline for this contract logistics prospect.

Lead details:
{lead_context(lead)}

Output sections:
1. Prospect Overview
2. Likely Operational Pain Points
3. Recommended Services
4. Sales Angle
5. Discovery Questions
6. Proposed Meeting Agenda
7. Executive Summary Paragraph

Keep it practical, suitable for a sales manager to review before approaching the prospect.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You create practical contract logistics proposal outlines."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.3,
    )
    return {"asset_type": "proposal_outline", "content": (response.choices[0].message.content or "").strip()}
