from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def analyze_lead_with_ai(
    lead: dict[str, Any],
    target_service: str,
    model: str = "gpt-4.1-mini",
) -> dict[str, Any]:
    prompt = f"""You are a contract logistics sales analyst.

Analyze this business as a potential lead for logistics services.
Target services we offer: {target_service}

Company info:
- Name: {lead.get('name', '')}
- Address: {lead.get('address', '')}
- Phone: {lead.get('phone', '')}
- Website: {lead.get('website', '')}
- Business type: {lead.get('primary_type', '')} | {lead.get('types', '')}
- Google Maps rating: {lead.get('rating', '')} ({lead.get('user_rating_count', '')} reviews)

Return ONLY a raw JSON object (no markdown) with these exact keys:
- lead_score: integer 1-10
- priority: one of "High", "Medium", "Low"
- logistics_potential: one sentence
- suggested_service: specific service from our offerings
- possible_pain_points: comma-separated list
- reasoning_summary: 2-3 sentences
- sales_opening_line: one punchy opening line for cold outreach
- email_subject: email subject line
- email_body: 3-paragraph professional email body
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
