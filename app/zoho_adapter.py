import json
import os
import urllib.parse
import urllib.request

from app.adapters import contact_status, safe_int, upsert_sheet_lead
from app import db


class ZohoCrmAdapter:
    def __init__(self):
        self.client_id = os.environ.get("ZOHO_CLIENT_ID")
        self.client_secret = os.environ.get("ZOHO_CLIENT_SECRET")
        self.refresh_token = os.environ.get("ZOHO_REFRESH_TOKEN")
        self.accounts_url = os.environ.get("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
        self.api_base = os.environ.get("ZOHO_API_BASE", "https://www.zohoapis.com")
        self.module = os.environ.get("ZOHO_MODULE", "Leads")
        self.per_page = int(os.environ.get("ZOHO_PER_PAGE", "100"))

    def configured(self):
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def sync(self):
        if not self.configured():
            return 0
        token = self.access_token()
        records = self.fetch_records(token)
        imported = 0
        for record in records:
            lead = normalize_zoho_record(record)
            if not lead["name"]:
                continue
            upsert_sheet_lead(lead)
            imported += 1
        db.event(None, "zoho_sync", f"Imported {imported} leads from Zoho CRM.")
        return imported

    def access_token(self):
        url = f"{self.accounts_url}/oauth/v2/token"
        payload = urllib.parse.urlencode(
            {
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
            }
        ).encode()
        with urllib.request.urlopen(url, data=payload, timeout=30) as response:
            data = json.loads(response.read().decode())
        if "access_token" not in data:
            raise ValueError(f"Zoho token response missing access_token: {data}")
        return data["access_token"]

    def fetch_records(self, token):
        url = f"{self.api_base}/crm/v2/{self.module}?per_page={self.per_page}&sort_by=Modified_Time&sort_order=desc"
        request = urllib.request.Request(url, headers={"Authorization": f"Zoho-oauthtoken {token}"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
        return data.get("data", [])


def normalize_zoho_record(record):
    first_name = record.get("First_Name") or ""
    last_name = record.get("Last_Name") or ""
    company = record.get("Company") or record.get("Account_Name") or ""
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    name = full_name or company or record.get("Full_Name") or record.get("Lead_Name") or ""
    phone = record.get("Phone") or record.get("Mobile") or record.get("Email") or ""
    external_id = f"zoho:{record.get('id')}" if record.get("id") else ""
    notes = "\n".join(
        str(value)
        for value in (
            record.get("Description"),
            record.get("Lead_Status"),
            record.get("Lead_Source"),
            record.get("Email"),
            record.get("Website"),
        )
        if value
    )
    intent = map_intent(record)
    prospect_type = map_prospect_type(record)
    engagement = "today" if record.get("Modified_Time") else "within_7_days"
    fit = map_fit(record, notes)
    return {
        "external_id": external_id,
        "name": name,
        "phone": phone,
        "source": record.get("Lead_Source") or "zoho_crm",
        "budget": safe_int(record.get("Annual_Revenue") or record.get("Budget")),
        "urgency": engagement,
        "location": record.get("City") or record.get("State") or record.get("Country") or "",
        "notes": notes,
        "intent": intent,
        "prospect_type": prospect_type,
        "engagement": engagement,
        "fit": fit,
        "contact_status": contact_status(phone, external_id),
    }


def map_intent(record):
    text = " ".join(str(record.get(key) or "") for key in ("Description", "Lead_Status", "Lead_Source")).lower()
    if "demo" in text or "meeting" in text:
        return "requested_demo"
    if "pricing" in text or "quote" in text:
        return "asked_pricing"
    if record.get("Email"):
        return "replied_email"
    return "website_visit"


def map_prospect_type(record):
    text = " ".join(str(record.get(key) or "") for key in ("Company", "Industry", "Description")).lower()
    if "university" in text:
        return "large_university"
    if "college" in text or "group" in text:
        return "college_group"
    return "training_institute"


def map_fit(record, notes):
    text = " ".join([notes, str(record.get("Industry") or "")]).lower()
    if "automation" in text or "manual" in text or "admission" in text:
        return "manual_admissions"
    if "high volume" in text or "many leads" in text:
        return "high_inquiry_volume"
    return "moderate_fit"
