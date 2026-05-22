from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "data" / "leadradar.db"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    if item.get("scoring_breakdown_json"):
        try:
            item["scoring_breakdown"] = json.loads(item["scoring_breakdown_json"])
        except Exception:
            item["scoring_breakdown"] = {}
    return item


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                industry TEXT DEFAULT '',
                radius_km REAL DEFAULT 10,
                target_service TEXT DEFAULT '',
                owner TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                place_id TEXT,
                name TEXT NOT NULL,
                address TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                website TEXT DEFAULT '',
                google_maps_url TEXT DEFAULT '',
                rating TEXT DEFAULT '',
                user_rating_count TEXT DEFAULT '',
                business_status TEXT DEFAULT '',
                primary_type TEXT DEFAULT '',
                types TEXT DEFAULT '',
                lead_score INTEGER DEFAULT 0,
                priority TEXT DEFAULT '',
                logistics_potential TEXT DEFAULT '',
                suggested_service TEXT DEFAULT '',
                possible_pain_points TEXT DEFAULT '',
                reasoning_summary TEXT DEFAULT '',
                sales_opening_line TEXT DEFAULT '',
                email_subject TEXT DEFAULT '',
                email_body TEXT DEFAULT '',
                scoring_breakdown_json TEXT DEFAULT '',
                decision_maker_name TEXT DEFAULT '',
                decision_maker_title TEXT DEFAULT '',
                decision_maker_email TEXT DEFAULT '',
                decision_maker_phone TEXT DEFAULT '',
                linkedin_url TEXT DEFAULT '',
                assigned_to TEXT DEFAULT '',
                sales_stage TEXT DEFAULT 'New',
                next_follow_up_date TEXT DEFAULT '',
                last_contacted_date TEXT DEFAULT '',
                estimated_potential TEXT DEFAULT '',
                service_fit TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                source TEXT DEFAULT '',
                website_summary TEXT DEFAULT '',
                duplicate_of INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_leads_campaign_id ON leads(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(sales_stage);
            CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority);
            CREATE INDEX IF NOT EXISTS idx_leads_followup ON leads(next_follow_up_date);
            CREATE INDEX IF NOT EXISTS idx_leads_place_id ON leads(place_id);

            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE
            );
            """
        )


def create_campaign(data: dict[str, Any]) -> int:
    existing_name = (data.get("name") or "").strip()
    if not existing_name:
        existing_name = f"{data.get('industry', 'Campaign')} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO campaigns (name, location, industry, radius_km, target_service, owner, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                existing_name,
                data.get("location", ""),
                data.get("industry", ""),
                data.get("radius_km", 10),
                data.get("target_service", ""),
                data.get("owner", ""),
                now_iso(),
                now_iso(),
            ),
        )
        return int(cur.lastrowid)


def get_campaign(campaign_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        return row_to_dict(conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone())


def get_campaigns() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*,
                   COUNT(l.id) AS lead_count,
                   SUM(CASE WHEN l.priority = 'High' THEN 1 ELSE 0 END) AS high_priority_count
            FROM campaigns c
            LEFT JOIN leads l ON l.campaign_id = c.id
            GROUP BY c.id
            ORDER BY c.created_at DESC
            """
        ).fetchall()
        return [row_to_dict(row) for row in rows]


def normalize_key(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def duplicate_lookup(lead: dict[str, Any]) -> dict[str, Any] | None:
    place_id = normalize_key(lead.get("place_id"))
    name = normalize_key(lead.get("name"))
    address = normalize_key(lead.get("address"))

    with get_connection() as conn:
        if place_id:
            row = conn.execute("SELECT * FROM leads WHERE LOWER(place_id) = ? LIMIT 1", (place_id,)).fetchone()
            if row:
                return row_to_dict(row)

        if name and address:
            row = conn.execute(
                "SELECT * FROM leads WHERE LOWER(name) = ? AND LOWER(address) = ? LIMIT 1",
                (name, address),
            ).fetchone()
            if row:
                return row_to_dict(row)
    return None


LEAD_COLUMNS = [
    "campaign_id",
    "place_id",
    "name",
    "address",
    "phone",
    "website",
    "google_maps_url",
    "rating",
    "user_rating_count",
    "business_status",
    "primary_type",
    "types",
    "lead_score",
    "priority",
    "logistics_potential",
    "suggested_service",
    "possible_pain_points",
    "reasoning_summary",
    "sales_opening_line",
    "email_subject",
    "email_body",
    "scoring_breakdown_json",
    "decision_maker_name",
    "decision_maker_title",
    "decision_maker_email",
    "decision_maker_phone",
    "linkedin_url",
    "assigned_to",
    "sales_stage",
    "next_follow_up_date",
    "last_contacted_date",
    "estimated_potential",
    "service_fit",
    "notes",
    "source",
    "website_summary",
    "duplicate_of",
]


def prepare_lead_data(data: dict[str, Any]) -> dict[str, Any]:
    prepared = {col: data.get(col, "") for col in LEAD_COLUMNS}
    prepared["name"] = prepared.get("name") or "Unnamed Company"
    if data.get("scoring_breakdown") and not prepared.get("scoring_breakdown_json"):
        prepared["scoring_breakdown_json"] = json.dumps(data["scoring_breakdown"], ensure_ascii=False)
    if isinstance(prepared.get("lead_score"), str) and prepared["lead_score"].isdigit():
        prepared["lead_score"] = int(prepared["lead_score"])
    elif not prepared.get("lead_score"):
        prepared["lead_score"] = 0
    return prepared


def save_lead(data: dict[str, Any]) -> int:
    duplicate = duplicate_lookup(data)
    prepared = prepare_lead_data(data)

    if duplicate:
        update = {k: v for k, v in prepared.items() if v not in ("", None)}
        update["duplicate_of"] = duplicate.get("duplicate_of") or duplicate.get("id")
        update_lead(int(duplicate["id"]), update)
        return int(duplicate["id"])

    columns = LEAD_COLUMNS + ["created_at", "updated_at"]
    values = [prepared.get(col, "") for col in LEAD_COLUMNS] + [now_iso(), now_iso()]
    placeholders = ",".join("?" for _ in columns)
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO leads ({','.join(columns)}) VALUES ({placeholders})",
            values,
        )
        lead_id = int(cur.lastrowid)
        add_activity(lead_id, "Lead Created", f"Lead created from {prepared.get('source', 'manual')}.", conn=conn)
        return lead_id


def update_lead(lead_id: int, changes: dict[str, Any]) -> None:
    allowed = set(LEAD_COLUMNS)
    clean: dict[str, Any] = {}
    for key, value in changes.items():
        if key == "scoring_breakdown":
            clean["scoring_breakdown_json"] = json.dumps(value, ensure_ascii=False)
        elif key in allowed:
            clean[key] = value

    if not clean:
        return

    clean["updated_at"] = now_iso()
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = list(clean.values()) + [lead_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE leads SET {assignments} WHERE id = ?", values)


def delete_lead(lead_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))


def get_lead(lead_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        lead = row_to_dict(conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone())
        if lead:
            activities = conn.execute(
                "SELECT * FROM activities WHERE lead_id = ? ORDER BY created_at DESC LIMIT 25",
                (lead_id,),
            ).fetchall()
            lead["activities"] = [row_to_dict(row) for row in activities]
        return lead


def get_leads(
    campaign_id: int | None = None,
    stage: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if campaign_id:
        clauses.append("campaign_id = ?")
        params.append(campaign_id)
    if stage:
        clauses.append("sales_stage = ?")
        params.append(stage)
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if assigned_to:
        clauses.append("assigned_to = ?")
        params.append(assigned_to)
    if query:
        clauses.append(
            "(LOWER(name) LIKE ? OR LOWER(address) LIKE ? OR LOWER(notes) LIKE ? OR LOWER(suggested_service) LIKE ?)"
        )
        q = f"%{query.lower()}%"
        params.extend([q, q, q, q])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as conn:
        rows = conn.execute(f"SELECT * FROM leads {where} ORDER BY updated_at DESC", params).fetchall()
        return [row_to_dict(row) for row in rows]


def add_activity(lead_id: int, activity_type: str, note: str = "", conn: sqlite3.Connection | None = None) -> None:
    own_conn = conn is None
    connection = conn or get_connection()
    try:
        connection.execute(
            "INSERT INTO activities (lead_id, activity_type, note, created_at) VALUES (?, ?, ?, ?)",
            (lead_id, activity_type, note, now_iso()),
        )
    finally:
        if own_conn:
            connection.commit()
            connection.close()


def get_due_followups(days: int = 7) -> list[dict[str, Any]]:
    end_date = (date.today() + timedelta(days=days)).isoformat()
    today = date.today().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM leads
            WHERE next_follow_up_date != ''
              AND next_follow_up_date <= ?
              AND sales_stage NOT IN ('Won', 'Lost')
            ORDER BY next_follow_up_date ASC
            """,
            (end_date,),
        ).fetchall()
    leads = [row_to_dict(row) for row in rows]
    for lead in leads:
        lead["overdue"] = bool(lead.get("next_follow_up_date") and lead["next_follow_up_date"] < today)
    return leads


def get_dashboard() -> dict[str, Any]:
    with get_connection() as conn:
        total_leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        high_priority = conn.execute("SELECT COUNT(*) FROM leads WHERE priority = 'High'").fetchone()[0]
        meetings = conn.execute("SELECT COUNT(*) FROM leads WHERE sales_stage = 'Meeting'").fetchone()[0]
        proposals = conn.execute("SELECT COUNT(*) FROM leads WHERE sales_stage = 'Proposal'").fetchone()[0]
        won = conn.execute("SELECT COUNT(*) FROM leads WHERE sales_stage = 'Won'").fetchone()[0]
        lost = conn.execute("SELECT COUNT(*) FROM leads WHERE sales_stage = 'Lost'").fetchone()[0]
        due = len(get_due_followups(7))

        stage_rows = conn.execute(
            "SELECT sales_stage, COUNT(*) AS count FROM leads GROUP BY sales_stage ORDER BY count DESC"
        ).fetchall()
        priority_rows = conn.execute(
            "SELECT priority, COUNT(*) AS count FROM leads GROUP BY priority ORDER BY count DESC"
        ).fetchall()
        campaign_rows = conn.execute(
            """
            SELECT c.name, COUNT(l.id) AS count
            FROM campaigns c LEFT JOIN leads l ON l.campaign_id = c.id
            GROUP BY c.id
            ORDER BY count DESC
            LIMIT 10
            """
        ).fetchall()

    return {
        "totals": {
            "leads": total_leads,
            "high_priority": high_priority,
            "meetings": meetings,
            "proposals": proposals,
            "won": won,
            "lost": lost,
            "followups_due_7_days": due,
        },
        "by_stage": [dict(row) for row in stage_rows],
        "by_priority": [dict(row) for row in priority_rows],
        "top_campaigns": [dict(row) for row in campaign_rows],
    }


def save_imported_leads(records: list[dict[str, Any]], campaign_id: int | None = None) -> int:
    inserted = 0
    for record in records:
        mapped = {str(k).strip().lower().replace(" ", "_"): v for k, v in record.items()}
        lead = {
            "campaign_id": campaign_id,
            "name": mapped.get("name") or mapped.get("company") or mapped.get("company_name") or "",
            "address": mapped.get("address", ""),
            "phone": mapped.get("phone", ""),
            "website": mapped.get("website", ""),
            "priority": mapped.get("priority", ""),
            "sales_stage": mapped.get("sales_stage") or mapped.get("stage") or "Imported",
            "assigned_to": mapped.get("assigned_to", ""),
            "notes": mapped.get("notes", ""),
            "source": "Excel Import",
            "service_fit": mapped.get("service_fit") or mapped.get("suggested_service") or "",
        }
        if lead["name"]:
            save_lead(lead)
            inserted += 1
    return inserted
