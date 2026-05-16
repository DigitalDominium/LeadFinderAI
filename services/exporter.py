from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def export_leads_to_excel(leads: list[dict[str, Any]], output_path: Path) -> Path:
    columns = [
        "name", "address", "phone", "website", "google_maps_url",
        "rating", "user_rating_count", "business_status", "primary_type",
        "lead_score", "priority", "logistics_potential", "suggested_service",
        "possible_pain_points", "reasoning_summary", "sales_opening_line",
        "email_subject", "email_body",
    ]

    rows = []
    for lead in leads:
        rows.append({col: lead.get(col, "") for col in columns})

    df = pd.DataFrame(rows, columns=columns)
    df.columns = [c.replace("_", " ").title() for c in df.columns]
    df.to_excel(output_path, index=False, engine="openpyxl")
    return output_path
