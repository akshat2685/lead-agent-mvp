import csv
import os
import urllib.request
from io import StringIO

from app import db
from app.sicada_adapter import SicadaCallAdapter
from app.vapi_adapter import VapiCallAdapter


class MockCrmAdapter:
    def sync(self):
        db.seed_demo_leads()
        db.event(None, "crm_sync", "Demo CRM sync completed.")


class GoogleSheetLeadAdapter:
    REQUIRED_COLUMNS = {
        "name",
        "phone",
        "source",
        "location",
        "intent",
        "prospect_type",
        "engagement",
        "fit",
    }
    DISCOVERY_COLUMNS = {
        "name/business",
        "platform",
        "contact_info",
        "post/snippet",
        "url",
        "priority_level",
        "date",
    }

    def __init__(self, csv_url=None):
        self.csv_url = to_csv_url(
            csv_url
            or os.environ.get("GOOGLE_SHEET_CSV_URL")
            or os.environ.get("GOOGLE_SHEET_URL")
        )

    def sync(self):
        if not self.csv_url:
            return 0
        with urllib.request.urlopen(self.csv_url, timeout=30) as response:
            content = response.read().decode("utf-8-sig")
        if content.lstrip().lower().startswith("<!doctype html") or "Sign in to your Google Account" in content:
            raise ValueError("Google Sheet is not publicly readable as CSV.")
        reader = csv.DictReader(StringIO(content))
        headers = {clean_key(header) for header in (reader.fieldnames or [])}
        is_structured = self.REQUIRED_COLUMNS.issubset(headers)
        is_discovery = self.DISCOVERY_COLUMNS.issubset(headers)
        if not is_structured and not is_discovery:
            missing = self.REQUIRED_COLUMNS - headers
            raise ValueError(f"Google Sheet is missing columns: {', '.join(sorted(missing))}")

        imported = 0
        for raw in reader:
            lead = normalize_row(raw, source_format="discovery" if is_discovery else "structured")
            if not lead["name"] or not lead["phone"]:
                continue
            upsert_sheet_lead(lead)
            imported += 1
        db.event(None, "sheet_sync", f"Imported {imported} leads from Google Sheet.")
        return imported


class VoiceCallAdapter:
    def call(self, lead):
        provider = os.environ.get("VOICE_PROVIDER", "mock").lower()
        if provider == "vapi":
            return VapiCallAdapter().call(lead)
        if provider == "sicada":
            return SicadaCallAdapter().call(lead)
        # Replace this with Twilio, Exotel, or another provider for real calls.
        attempt = int(lead["attempts"]) + 1
        if attempt == 1 and lead["priority"] == "Hot":
            outcome = "connected"
            summary = "Simulated voice agent connected and qualified the lead."
        else:
            outcome = "no_response"
            summary = "Simulated call placed. Customer did not answer."
        return {"outcome": outcome, "summary": summary}


def clean_key(value):
    key = (value or "").strip().lower().replace(" ", "_")
    aliases = {
        "platform_m": "platform",
        "platformm": "platform",
    }
    return aliases.get(key, key)


def to_csv_url(url):
    if not url:
        return None
    if "/export?" in url:
        return url
    if "docs.google.com/spreadsheets/d/" not in url:
        return url
    sheet_id = url.split("/d/", 1)[1].split("/", 1)[0]
    gid = "0"
    if "gid=" in url:
        gid = url.split("gid=", 1)[1].split("#", 1)[0].split("&", 1)[0]
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def normalize_row(raw, source_format="structured"):
    row = {clean_key(key): (value or "").strip() for key, value in raw.items()}
    if source_format == "discovery":
        return normalize_discovery_row(row)
    phone = row.get("phone", "")
    return {
        "external_id": row.get("external_id") or row.get("id") or "",
        "name": row.get("name", ""),
        "phone": phone,
        "source": row.get("source") or "google_sheet",
        "budget": int(row.get("budget") or 0),
        "urgency": row.get("urgency") or row.get("engagement") or "unknown",
        "location": row.get("location") or "",
        "notes": row.get("notes") or "",
        "intent": row.get("intent") or "website_visit",
        "prospect_type": row.get("prospect_type") or "training_institute",
        "engagement": row.get("engagement") or "stale_30_days",
        "fit": row.get("fit") or "moderate_fit",
        "contact_status": contact_status(phone, row.get("external_id") or row.get("id") or ""),
    }


def normalize_zapier_payload(raw):
    row = {clean_key(key): str(value or "").strip() for key, value in raw.items()}
    if row.get("name/business") or row.get("priority_level"):
        return normalize_discovery_row(row)
    phone = row.get("phone") or row.get("contact_info") or row.get("contact") or ""
    external_id = row.get("external_id") or row.get("id") or row.get("url") or ""
    return {
        "external_id": external_id,
        "name": row.get("name") or row.get("business_name") or row.get("lead_name") or "",
        "phone": phone,
        "source": row.get("source") or row.get("platform") or "zapier",
        "budget": safe_int(row.get("budget")),
        "urgency": row.get("urgency") or row.get("engagement") or "today",
        "location": row.get("location") or "",
        "notes": row.get("notes") or row.get("post/snippet") or row.get("snippet") or "",
        "intent": row.get("intent") or intent_from_priority(row),
        "prospect_type": row.get("prospect_type") or "training_institute",
        "engagement": row.get("engagement") or "today",
        "fit": row.get("fit") or fit_from_text(row),
        "contact_status": contact_status(phone, external_id),
    }


def normalize_discovery_row(row):
    priority = row.get("priority_level", "").lower()
    snippet = row.get("post/snippet", "")
    url = row.get("url", "")
    text = f"{priority} {snippet}".lower()

    if "urgent" in priority or "asap" in text or "need" in text:
        intent = "requested_demo"
    elif "high" in priority or "voice agent" in text or "automation" in text:
        intent = "asked_pricing"
    elif "standard" in priority:
        intent = "replied_email"
    else:
        intent = "website_visit"

    if "urgent" in priority:
        fit = "high_inquiry_volume"
    elif "automation" in text or "voice agent" in text or "lead generation" in text:
        fit = "manual_admissions"
    else:
        fit = "moderate_fit"

    if "team" in text or "business owner" in text or "startup" in text:
        prospect_type = "medium_university"
    else:
        prospect_type = "training_institute"

    contact = row.get("contact_info", "")
    phone = contact if is_real_contact(contact) else f"sheet:{url}"
    notes = snippet
    if url:
        notes = f"{snippet}\nURL: {url}"
    if row.get("date"):
        notes = f"{notes}\nDate: {row['date']}"

    return {
        "external_id": url,
        "name": row.get("name/business", ""),
        "phone": phone,
        "source": row.get("platform") or "leads_agent",
        "budget": 0,
        "urgency": "today",
        "location": "",
        "notes": notes,
        "intent": intent,
        "prospect_type": prospect_type,
        "engagement": "today",
        "fit": fit,
        "contact_status": contact_status(phone, url),
    }


def intent_from_priority(row):
    text = " ".join([row.get("priority_level", ""), row.get("notes", ""), row.get("snippet", "")]).lower()
    if "urgent" in text or "asap" in text or "need" in text:
        return "requested_demo"
    if "high" in text or "voice agent" in text or "automation" in text:
        return "asked_pricing"
    if "standard" in text:
        return "replied_email"
    return "website_visit"


def fit_from_text(row):
    text = " ".join([row.get("priority_level", ""), row.get("notes", ""), row.get("snippet", "")]).lower()
    if "urgent" in text:
        return "high_inquiry_volume"
    if "automation" in text or "voice agent" in text or "lead generation" in text:
        return "manual_admissions"
    return "moderate_fit"


def safe_int(value):
    try:
        return int(value or 0)
    except ValueError:
        return 0


def is_real_contact(value):
    cleaned = (value or "").strip().lower()
    return bool(cleaned and cleaned not in ("not available", "not_available", "n/a", "na", "none", "-"))


def contact_status(phone, external_id=""):
    cleaned = (phone or "").strip().lower()
    if cleaned.startswith("sheet:") or cleaned.startswith("zapier:"):
        return "has_url_only" if external_id else "not_contactable"
    if is_real_contact(phone):
        if any(char.isdigit() for char in phone):
            return "has_phone"
        return "needs_manual_contact"
    return "has_url_only" if external_id else "not_contactable"


def upsert_sheet_lead(lead):
    tombstone = lead["external_id"] or lead["phone"]
    if tombstone and db.row("select key from deleted_leads where key = ?", (tombstone,)):
        return
    if lead["external_id"]:
        existing = db.row("select id from leads where external_id = ?", (lead["external_id"],))
    else:
        existing = db.row("select id from leads where phone = ?", (lead["phone"],))
    if existing:
        db.execute(
            """
            update leads
            set external_id = ?, name = ?, source = ?, budget = ?, urgency = ?,
                location = ?, notes = ?, intent = ?, prospect_type = ?,
                engagement = ?, fit = ?, contact_status = ?
            where id = ?
            """,
            (
                lead["external_id"],
                lead["name"],
                lead["source"],
                lead["budget"],
                lead["urgency"],
                lead["location"],
                lead["notes"],
                lead["intent"],
                lead["prospect_type"],
                lead["engagement"],
                lead["fit"],
                lead["contact_status"],
                existing["id"],
            ),
        )
        return
    db.execute(
        """
        insert into leads(
            external_id, name, phone, source, budget, urgency, location, notes,
            intent, prospect_type, engagement, fit, contact_status
        )
        values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead["external_id"],
            lead["name"],
            lead["phone"],
            lead["source"],
            lead["budget"],
            lead["urgency"],
            lead["location"],
            lead["notes"],
            lead["intent"],
            lead["prospect_type"],
            lead["engagement"],
            lead["fit"],
            lead["contact_status"],
        ),
    )


def import_zapier_lead(payload):
    lead = normalize_zapier_payload(payload)
    if not lead["name"]:
        raise ValueError("Missing lead name.")
    if not lead["phone"]:
        lead["phone"] = f"zapier:{lead['external_id'] or lead['name']}"
    upsert_sheet_lead(lead)
    imported = db.row(
        "select * from leads where external_id = ?",
        (lead["external_id"],),
    ) if lead["external_id"] else None
    if not imported:
        imported = db.row("select * from leads where phone = ?", (lead["phone"],))
    db.event(imported["id"] if imported else None, "zapier_import", f"Imported lead from Zapier: {lead['name']}.")
    return imported
