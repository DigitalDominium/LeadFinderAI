from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL        = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

DEFAULT_EXPORT_FOLDER = BASE_DIR / "exports"
DEFAULT_EXPORT_FOLDER.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "leads.db"

# Pipeline stages in order
PIPELINE_STAGES = ["New", "Contacted", "Meeting", "Proposal", "Won", "Lost"]

STAGE_COLORS = {
    "New":       "#3B82F6",
    "Contacted": "#F59E0B",
    "Meeting":   "#8B5CF6",
    "Proposal":  "#EC4899",
    "Won":       "#10B981",
    "Lost":      "#6B7280",
}

PRIORITY_COLORS = {
    "HIGH":   "#EF4444",
    "MEDIUM": "#F59E0B",
    "LOW":    "#6B7280",
}
