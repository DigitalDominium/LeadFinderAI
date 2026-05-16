from __future__ import annotations

import os
import tempfile
from pathlib import Path

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe audio bytes using OpenAI Whisper."""
    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=(Path(tmp_path).name, f, "audio/webm"),
                language="en",
            )
        return transcript.text.strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def text_to_speech(text: str) -> bytes:
    """Convert text to speech using OpenAI TTS. Returns mp3 bytes."""
    # Truncate very long text for TTS - summarise if needed
    if len(text) > 1000:
        text = text[:1000] + "..."

    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx",   # Deep, authoritative voice - fits Dominium LeadRadar persona
        input=text,
        response_format="mp3",
    )
    return response.content


def interpret_command(text: str) -> dict:
    """
    Use GPT to interpret a voice command and extract structured intent.
    Returns a dict with: intent, params, response_text
    """
    system_prompt = """You are Dominium LeadRadar, an AI assistant for a contract logistics sales team.
You help find B2B leads, analyze companies, and support sales prospecting.

When the user speaks a command, extract the intent and parameters, and provide a brief spoken response.

Return ONLY a JSON object with these fields:
- "intent": one of ["search_leads", "analyze_leads", "export_leads", "linkedin_people", "linkedin_company", "clear", "help", "unknown"]
- "params": object with relevant extracted parameters:
  - for search_leads: {"location": "...", "industry": "...", "radius_km": number, "count": number, "target_service": "..."}
  - for others: {} or relevant fields
- "response_text": a short Jarvis-style spoken response (1-2 sentences, confident and direct)

Examples:
- "Find me 10 manufacturing companies in Johor Bahru" → intent: search_leads
- "Analyze the leads" → intent: analyze_leads  
- "Export to Excel" → intent: export_leads
- "Find people at this company" → intent: linkedin_people
- "Show me the company page" → intent: linkedin_company
- "Clear the results" → intent: clear

Default values if not specified: radius_km=10, count=10, target_service="Warehousing, VAS, inventory management"
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        max_tokens=300,
        temperature=0,
    )

    import json
    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if present
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
