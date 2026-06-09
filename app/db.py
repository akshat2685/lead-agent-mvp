import json
import os
from contextlib import contextmanager
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "sales_agent")
DB_USER = os.getenv("DB_USER", "ijain")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

LEAD_COLUMNS = {
    "name",
    "phone",
    "email",
    "company",
    "raw_text",
    "response",
    "score",
    "bucket",
    "status",
    "source",
    "source_timestamp",
    "deduplicated_with_id",
    "created_at",
    "scored_at",
    "approved_at",
    "approved_by",
    "rejected_at",
    "rejection_reason",
    "scida_id",
    "assigned_channel",
    "call_queued_at",
    "voice_call_id",
    "chat_queued_at",
    "chat_message_id",
    "chat_delivered_at",
    "chat_read_at",
    "chat_replied_at",
    "chat_reply",
    "last_contact_date",
    "call_duration",
    "call_transcript",
    "call_sentiment",
    "outcome",
    "outcome_date",
    "intent",
    "engagement",
    "company_size",
    "voice_script",
    "script_generated_at",
    "zoho_lead_id",
    "zoho_contact_id",
    "zoho_account_id",
    "zoho_deal_id",
    "zoho_owner_id",
    "zoho_synced_at",
    "zoho_sync_status",
    "zoho_sync_payload",
    "outreach_channel",
    "manual_review_required",
}


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


@contextmanager
def cursor():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def execute(query, params=None, returning=False):
    with cursor() as (conn, cur):
        cur.execute(query, params or ())
        if returning:
            return cur.fetchone()
        return cur.rowcount


def fetch_one(query, params=None):
    with cursor() as (conn, cur):
        cur.execute(query, params or ())
        return cur.fetchone()


def fetch_all(query, params=None):
    with cursor() as (conn, cur):
        cur.execute(query, params or ())
        return cur.fetchall()


def init_database():
    with cursor() as (conn, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                name TEXT,
                phone TEXT,
                email TEXT,
                company TEXT,
                raw_text TEXT,
                response TEXT,
                score INTEGER,
                bucket TEXT,
                status TEXT DEFAULT 'new',
                source TEXT DEFAULT 'telegram',
                source_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deduplicated_with_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scored_at TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by TEXT,
                rejected_at TIMESTAMP,
                rejection_reason TEXT,
                scida_id TEXT,
                assigned_channel TEXT,
                call_queued_at TIMESTAMP,
                voice_call_id TEXT,
                chat_queued_at TIMESTAMP,
                chat_message_id TEXT,
                chat_delivered_at TIMESTAMP,
                chat_read_at TIMESTAMP,
                chat_replied_at TIMESTAMP,
                chat_reply TEXT,
                last_contact_date TIMESTAMP,
                call_duration INTEGER,
                call_transcript TEXT,
                call_sentiment TEXT,
                outcome TEXT,
                outcome_date TIMESTAMP,
                intent TEXT,
                engagement TEXT,
                company_size TEXT,
                voice_script TEXT,
                script_generated_at TIMESTAMP,
                zoho_lead_id TEXT,
                zoho_contact_id TEXT,
                zoho_account_id TEXT,
                zoho_deal_id TEXT,
                zoho_owner_id TEXT,
                zoho_synced_at TIMESTAMP,
                zoho_sync_status TEXT,
                zoho_sync_payload TEXT,
                outreach_channel TEXT,
                manual_review_required BOOLEAN DEFAULT FALSE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_history (
                id SERIAL PRIMARY KEY,
                lead_id INTEGER NOT NULL REFERENCES leads(id),
                action TEXT NOT NULL,
                notes TEXT,
                changed_by TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversions (
                id SERIAL PRIMARY KEY,
                lead_id INTEGER NOT NULL REFERENCES leads(id),
                predicted_score INTEGER,
                predicted_bucket TEXT,
                actual_outcome TEXT,
                features TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for statement in (
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS name TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS phone TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS email TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS company TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS raw_text TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS response TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS score INTEGER",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS bucket TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'new'",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'telegram'",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS deduplicated_with_id INTEGER",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS scored_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS approved_by TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS rejection_reason TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS scida_id TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS assigned_channel TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS call_queued_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS voice_call_id TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS chat_queued_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS chat_message_id TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS chat_delivered_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS chat_read_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS chat_replied_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS chat_reply TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_contact_date TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS call_duration INTEGER",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS call_transcript TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS call_sentiment TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS outcome TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS outcome_date TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS intent TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS engagement TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS company_size TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS voice_script TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS script_generated_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS zoho_lead_id TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS zoho_contact_id TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS zoho_account_id TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS zoho_deal_id TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS zoho_owner_id TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS zoho_synced_at TIMESTAMP",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS zoho_sync_status TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS zoho_sync_payload TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS outreach_channel TEXT",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS manual_review_required BOOLEAN DEFAULT FALSE",
        ):
            cur.execute(statement)


def normalize_payload(payload):
    normalized = {}
    for key, value in payload.items():
        if key not in LEAD_COLUMNS:
            continue
        if isinstance(value, datetime):
            normalized[key] = value
        elif isinstance(value, (int, float, bool)):
            normalized[key] = value
        elif value is None:
            normalized[key] = None
        else:
            text = str(value).strip()
            normalized[key] = text or None
    return normalized


def insert_lead(payload):
    data = normalize_payload(payload)
    if not data:
        raise ValueError("Lead payload is empty")
    columns = list(data.keys())
    values = [data[column] for column in columns]
    placeholders = ", ".join(["%s"] * len(values))
    sql = f"""
        INSERT INTO leads ({", ".join(columns)})
        VALUES ({placeholders})
        RETURNING id
    """
    row = execute(sql, values, returning=True)
    return row["id"]


def update_lead(lead_id, changes):
    data = normalize_payload(changes)
    if not data:
        return 0
    assignments = ", ".join(f"{column} = %s" for column in data)
    sql = f"UPDATE leads SET {assignments} WHERE id = %s"
    params = list(data.values()) + [lead_id]
    return execute(sql, params)


def query_lead(lead_id):
    return fetch_one("SELECT * FROM leads WHERE id = %s", (lead_id,))


def query_lead_by_zoho_id(zoho_lead_id):
    return fetch_one("SELECT * FROM leads WHERE zoho_lead_id = %s", (str(zoho_lead_id),))


def find_duplicate(lead_data, source):
    phone = lead_data.get("phone")
    email = lead_data.get("email")
    return fetch_one(
        """
        SELECT id, source
        FROM leads
        WHERE source <> %s
          AND (
                (%s IS NOT NULL AND phone = %s)
             OR (%s IS NOT NULL AND email = %s)
          )
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (source, phone, phone, email, email),
    )


def log_action(lead_id, action, notes="", changed_by="system"):
    return execute(
        """
        INSERT INTO lead_history (lead_id, action, notes, changed_by, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (lead_id, action, notes, changed_by, datetime.now()),
    )


def get_lead_history(lead_id):
    return fetch_all(
        """
        SELECT action, notes, changed_by, timestamp
        FROM lead_history
        WHERE lead_id = %s
        ORDER BY timestamp DESC
        """,
        (lead_id,),
    )


def get_dedup_report():
    stats = fetch_one(
        """
        SELECT
            COUNT(*) AS total_leads,
            COUNT(DISTINCT source) AS sources_count,
            COUNT(*) FILTER (WHERE deduplicated_with_id IS NOT NULL) AS duplicates_found
        FROM leads
        """
    ) or {"total_leads": 0, "sources_count": 0, "duplicates_found": 0}
    by_source = fetch_all(
        """
        SELECT source, COUNT(*) AS count
        FROM leads
        WHERE deduplicated_with_id IS NULL
        GROUP BY source
        ORDER BY count DESC, source ASC
        """
    )
    return stats, by_source


def list_pending_review():
    return fetch_all(
        """
        SELECT *
        FROM leads
        WHERE status IN ('pending_approval', 'reviewed')
           OR manual_review_required = TRUE
        ORDER BY scored_at DESC NULLS LAST, created_at DESC
        """
    )


def list_unlinked_zoho_leads():
    return fetch_all(
        """
        SELECT *
        FROM leads
        WHERE zoho_lead_id IS NULL
        ORDER BY created_at DESC
        """
    )


def log_conversion(lead_id, predicted_score, predicted_bucket, actual_outcome, features):
    payload = json.dumps(features, default=str)
    return execute(
        """
        INSERT INTO conversions (lead_id, predicted_score, predicted_bucket, actual_outcome, features, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            lead_id,
            predicted_score,
            predicted_bucket,
            actual_outcome,
            payload,
            datetime.now(),
        ),
    )


def count(query, params=None):
    row = fetch_one(query, params)
    if not row:
        return 0
    value = next(iter(row.values()))
    return int(value or 0)
