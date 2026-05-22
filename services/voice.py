from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from openai import OpenAI


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in Render environment variables.")
    return OpenAI(api_key=api_key)


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    suffix = Path(filename).suffix or ".webm"
    client = get_client()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = Path(tmp.name)
    try:
        with tmp_path.open("rb") as file_obj:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=(tmp_path.name, file_obj, "audio/webm"),
                language="en",
            )
        return transcript.text.strip()
    finally:
        tmp_path.unlink(missing_ok=True)


def text_to_speech(text: str) -> bytes:
    client = get_client()
    text = (text or "")[:1200]
    response = client.audio.speech.create(
        model="tts-1",
        voice=os.getenv("OPENAI_TTS_VOICE", "onyx"),
        input=text,
        response_format="mp3",
    )
    return response.content


def interpret_command(text: str) -> dict:
    client = get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    system_prompt = """
You are Dominium LeadRadar, an AI assistant for a contract logistics sales team.
Extract intent from voice commands.

Return ONLY JSON with:
{
  "intent": one of ["search_leads","analyze_leads","show_dashboard","show_followups","export_leads","clear","help","unknown"],
  "params": {
    "location": "",
    "industry": "",
    "radius_km": 10,
    "count": 10,
    "target_service": ""
  },
  "response_text": "short confident response"
}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        max_tokens=300,
        temperature=0,
    )
    raw = (response.choices[0].message.content or "{}").strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
