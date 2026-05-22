from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in Render environment variables.")
    return OpenAI(api_key=api_key)


def extract_json(raw: str) -> dict[str, Any]:
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if match:
            return json.loads(match.group(0))
        raise


def analyze_lead_with_ai(
    lead: dict[str, Any],
    target_service: str,
    model: str | None = None,
) -> dict[str, Any]:
    model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = get_client()

    prompt = f"""
You are a senior contract logistics sales analyst. Score and qualify this company as a B2B prospect.

Target services offered:
{target_service}

Company information:
- Name: {lead.get('name', '')}
- Address: {lead.get('address', '')}
- Phone: {lead.get('phone', '')}
- Website: {lead.get('website', '')}
- Business type: {lead.get('primary_type', '')} | {lead.get('types', '')}
- Google Maps rating: {lead.get('rating', '')} ({lead.get('user_rating_count', '')} reviews)
- Website summary, if available: {lead.get('website_summary', '')}
- Current notes, if any: {lead.get('notes', '')}

Return ONLY a valid raw JSON object. Do not use markdown.
Use this exact structure:
{{
  "lead_score": 0-100,
  "priority": "High" or "Medium" or "Low",
  "estimated_potential": "High" or "Medium" or "Low",
  "service_fit": "short service category",
  "logistics_potential": "one sentence",
  "suggested_service": "specific service from our offerings",
  "possible_pain_points": "comma-separated list",
  "reasoning_summary": "2-3 sentences",
  "sales_opening_line": "one strong cold outreach line",
  "email_subject": "subject line",
  "email_body": "3 short professional paragraphs",
  "scoring_breakdown": {{
    "industry_fit": 0-30,
    "location_fit": 0-20,
    "logistics_need": 0-30,
    "company_visibility": 0-10,
    "contact_availability": 0-10
  }}
}}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You return clean JSON only. No markdown."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=900,
        temperature=0.25,
    )
    raw = response.choices[0].message.content or "{}"
    data = extract_json(raw)

    score = int(data.get("lead_score") or 0)
    data["lead_score"] = max(0, min(score, 100))
    if not data.get("priority"):
        data["priority"] = "High" if score >= 75 else "Medium" if score >= 45 else "Low"
    return data
