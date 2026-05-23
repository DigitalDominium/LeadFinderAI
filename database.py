from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DB_PATH


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id        TEXT UNIQUE,
            name            TEXT,
            address         TEXT,
            phone           TEXT,
            website         TEXT,
            google_maps_url TEXT,
            business_status TEXT,
            rating          REAL,
            user_rating_count INTEGER,
            primary_type    TEXT,
            types           TEXT,
            -- AI fields
            lead_score      INTEGER,
            priority        TEXT,
            logistics_potential TEXT,
            suggested_service   TEXT,
            possible_pain_points TEXT,
            reasoning_summary   TEXT,
            sales_opening_line  TEXT,
            email_subject       TEXT,
            email_body          TEXT,
            -- CRM fields
            stage           TEXT DEFAULT 'New',
            notes           TEXT DEFAULT '',
            follow_up_date  TEXT DEFAULT '',
            last_contacted  TEXT DEFAULT '',
            contact_name    TEXT DEFAULT '',
            contact_role    TEXT DEFAULT '',
            whatsapp_draft  TEXT DEFAULT '',
            created_at      TEXT,
            updated_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS activities (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id    INTEGER,
            action     TEXT,
            note       TEXT,
            created_at TEXT,
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        );
        """)


# ─── Lead CRUD ────────────────────────────────────────────────────────────────

def upsert_lead(data: dict[str, Any]) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    fields = [
        "place_id","name","address","phone","website","google_maps_url",
        "business_status","rating","user_rating_count","primary_type","types",
        "lead_score","priority","logistics_potential","suggested_service",
        "possible_pain_points","reasoning_summary","sales_opening_line",
        "email_subject","email_body",
    ]
    row = {f: data.get(f, None) for f in fields}
    row["created_at"] = now
    row["updated_at"] = now

    cols = ", ".join(row.keys())
    placeholders = ", ".join(f":{k}" for k in row.keys())
    update_clause = ", ".join(
        f"{k}=excluded.{k}" for k in row.keys() if k not in ("place_id","created_at")
    )

    with _conn() as con:
        cur = con.execute(
            f"""INSERT INTO leads ({cols}) VALUES ({placeholders})
                ON CONFLICT(place_id) DO UPDATE SET {update_clause}""",
            row,
        )
        # fetch the rowid
        row2 = con.execute(
            "SELECT id FROM leads WHERE place_id=?", (row["place_id"],)
        ).fetchone()
        return row2["id"] if row2 else cur.lastrowid


def update_lead_crm(lead_id: int, **kwargs) -> None:
    if not kwargs:
        return
    kwargs["updated_at"] = datetime.now().isoformat(timespec="seconds")
    set_clause = ", ".join(f"{k}=:{k}" for k in kwargs)
    kwargs["lead_id"] = lead_id
    with _conn() as con:
        con.execute(f"UPDATE leads SET {set_clause} WHERE id=:lead_id", kwargs)


def get_all_leads() -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM leads ORDER BY lead_score DESC, created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_leads_by_stage(stage: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM leads WHERE stage=? ORDER BY lead_score DESC", (stage,)).fetchall()
        return [dict(r) for r in rows]


def get_followups_due() -> list[dict]:
    today = datetime.now().date().isoformat()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM leads WHERE follow_up_date != '' AND follow_up_date <= ? AND stage NOT IN ('Won','Lost') ORDER BY follow_up_date",
            (today,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_lead(lead_id: int) -> None:
    with _conn() as con:
        con.execute("DELETE FROM leads WHERE id=?", (lead_id,))
        con.execute("DELETE FROM activities WHERE lead_id=?", (lead_id,))


def get_analytics() -> dict:
    with _conn() as con:
        total = con.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        by_stage = {row[0]: row[1] for row in con.execute(
            "SELECT stage, COUNT(*) FROM leads GROUP BY stage"
        ).fetchall()}
        by_priority = {row[0]: row[1] for row in con.execute(
            "SELECT priority, COUNT(*) FROM leads WHERE priority IS NOT NULL GROUP BY priority"
        ).fetchall()}
        avg_score = con.execute(
            "SELECT AVG(lead_score) FROM leads WHERE lead_score IS NOT NULL"
        ).fetchone()[0]
        top_leads = [dict(r) for r in con.execute(
            "SELECT name, lead_score, priority, stage FROM leads WHERE lead_score IS NOT NULL ORDER BY lead_score DESC LIMIT 5"
        ).fetchall()]
        return {
            "total": total,
            "by_stage": by_stage,
            "by_priority": by_priority,
            "avg_score": round(avg_score or 0, 1),
            "top_leads": top_leads,
        }


# ─── Activity log ─────────────────────────────────────────────────────────────

def log_activity(lead_id: int, action: str, note: str = "") -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as con:
        con.execute(
            "INSERT INTO activities (lead_id, action, note, created_at) VALUES (?,?,?,?)",
            (lead_id, action, note, now),
        )


def get_activities(lead_id: int) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM activities WHERE lead_id=? ORDER BY created_at DESC LIMIT 20",
            (lead_id,),
        ).fetchall()
        return [dict(r) for r in rows]
