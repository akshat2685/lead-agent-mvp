import sqlite3
import time
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "lead_agent.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as db:
        db.executescript(
            """
            create table if not exists leads (
                id integer primary key autoincrement,
                name text not null,
                phone text not null,
                source text not null,
                budget integer not null,
                urgency text not null,
                location text not null,
                status text not null default 'new',
                score integer not null default 0,
                priority text not null default 'Unscored',
                last_action_at integer,
                next_action_at integer,
                attempts integer not null default 0,
                notes text not null default ''
            );

            create table if not exists approvals (
                id integer primary key autoincrement,
                lead_id integer not null,
                action text not null,
                reason text not null,
                status text not null default 'pending',
                created_at integer not null,
                decided_at integer,
                foreign key (lead_id) references leads(id)
            );

            create table if not exists events (
                id integer primary key autoincrement,
                lead_id integer,
                kind text not null,
                message text not null,
                created_at integer not null,
                foreign key (lead_id) references leads(id)
            );

            create table if not exists settings (
                key text primary key,
                value text not null
            );

            create table if not exists deleted_leads (
                key text primary key,
                reason text not null,
                deleted_at integer not null
            );

            create table if not exists research_candidates (
                token text primary key,
                lead_id integer not null,
                contact text not null,
                created_at integer not null
            );
            """
        )
        migrate_leads(db)
        db.execute(
            "insert or ignore into settings(key, value) values('mode', 'approval')"
        )
        db.execute(
            "insert or ignore into settings(key, value) values('paused', 'false')"
        )
        db.commit()


def migrate_leads(db):
    columns = {row["name"] for row in db.execute("pragma table_info(leads)").fetchall()}
    additions = {
        "intent": "text not null default 'website_visit'",
        "prospect_type": "text not null default 'training_institute'",
        "engagement": "text not null default 'stale_30_days'",
        "fit": "text not null default 'moderate_fit'",
        "external_id": "text not null default ''",
        "contact_status": "text not null default 'unknown'",
        "active_call_id": "text not null default ''",
        "last_call_provider": "text not null default ''",
    }
    for name, definition in additions.items():
        if name not in columns:
            db.execute(f"alter table leads add column {name} {definition}")


def seed_demo_leads():
    with connect() as db:
        exists = db.execute("select count(*) from leads").fetchone()[0]
        if exists:
            demo_updates = [
                ("ABC University", "Asked for a demo and pricing.", "requested_demo", "large_university", "today", "high_inquiry_volume", 1),
                ("XYZ College", "Asked pricing after multiple website visits.", "asked_pricing", "medium_university", "within_3_days", "manual_admissions", 2),
                ("PQR Institute", "Downloaded brochure only.", "downloaded_brochure", "training_institute", "within_7_days", "moderate_fit", 3),
                ("DEF University", "Admissions team asked pricing and wants automation.", "asked_pricing", "large_university", "today", "manual_admissions", 4),
                ("LMN College Group", "Website visit only, already uses advanced AI.", "website_visit", "college_group", "stale_30_days", "advanced_ai", 5),
            ]
            db.executemany(
                """
                update leads
                set name = ?, notes = ?, intent = ?, prospect_type = ?, engagement = ?, fit = ?
                where id = ?
                """,
                demo_updates,
            )
            db.commit()
            return
        leads = [
            ("ABC University", "+910000000001", "website", 800000, "today", "Mumbai", "Asked for a demo and pricing.", "requested_demo", "large_university", "today", "high_inquiry_volume"),
            ("XYZ College", "+910000000002", "referral", 350000, "this_week", "Delhi", "Asked pricing after multiple website visits.", "asked_pricing", "medium_university", "within_3_days", "manual_admissions"),
            ("PQR Institute", "+910000000003", "facebook", 90000, "unknown", "Pune", "Downloaded brochure only.", "downloaded_brochure", "training_institute", "within_7_days", "moderate_fit"),
            ("DEF University", "+910000000004", "google_ads", 600000, "today", "Bengaluru", "Admissions team asked pricing and wants automation.", "asked_pricing", "large_university", "today", "manual_admissions"),
            ("LMN College Group", "+910000000005", "walk_in", 250000, "this_month", "Jaipur", "Website visit only, already uses advanced AI.", "website_visit", "college_group", "stale_30_days", "advanced_ai"),
        ]
        db.executemany(
            """
            insert into leads(
                name, phone, source, budget, urgency, location, notes,
                intent, prospect_type, engagement, fit
            )
            values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            leads,
        )
        db.commit()


def now():
    return int(time.time())


def rows(query, params=()):
    with connect() as db:
        return [dict(row) for row in db.execute(query, params).fetchall()]


def row(query, params=()):
    with connect() as db:
        found = db.execute(query, params).fetchone()
        return dict(found) if found else None


def execute(query, params=()):
    with connect() as db:
        cur = db.execute(query, params)
        db.commit()
        return cur.lastrowid


def event(lead_id, kind, message):
    execute(
        "insert into events(lead_id, kind, message, created_at) values(?, ?, ?, ?)",
        (lead_id, kind, message, now()),
    )
