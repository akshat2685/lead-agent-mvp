import json

from . import db
from .agent import process_approved_lead


class ZohoCRMService:
    """Blank Zoho integration surface for future wiring."""

    def __init__(self):
        self.pipeline = ""
        self.stage = ""
        self.owner_id = ""
        self.team_review_threshold = 60

    def enabled(self):
        return False

    def sync_local_lead_to_zoho(self, lead_id, note_title="Scida sync", note_content=None):
        lead = db.query_lead(lead_id)
        if not lead:
            return {"error": "Lead not found"}
        zoho_payload = {
            "First_Name": lead["name"].split()[0] if lead.get("name") else "",
            "Last_Name": " ".join(lead["name"].split()[1:]) if lead.get("name") and len(lead["name"].split()) > 1 else (lead.get("name") or "Unknown"),
            "Email": lead.get("email"),
            "Phone": lead.get("phone"),
            "Company": lead.get("company") or "Unknown",
            "Lead_Source": lead.get("source"),
            "Description": lead.get("raw_text"),
            "Lead_Score": lead.get("score"),
            "Priority_Bucket": lead.get("bucket"),
            "Lead_Status": lead.get("status")
        }
        
        # In a real implementation, this hits Zoho's API
        # response = requests.post(f"{self.base_url}/Leads", headers=self.headers, json={"data": [zoho_payload]})
        
        db.update_lead(
            lead_id,
            {
                "zoho_synced_at": datetime.now(),
                "zoho_sync_status": "success",
                "zoho_sync_payload": json.dumps(zoho_payload),
                "zoho_lead_id": f"ZOHO_MOCK_{lead_id}",
            },
        )
        return {"status": "success", "lead_id": lead_id, "zoho_payload": zoho_payload}

    def sync_transcript_to_zoho(self, lead_id, transcript, sentiment, outcome):
        lead = db.query_lead(lead_id)
        if not lead or not lead.get("zoho_lead_id"):
            return {"error": "Lead not synced to Zoho"}
            
        note_payload = {
            "Parent_Id": lead.get("zoho_lead_id"),
            "Note_Title": f"Call Outcome: {outcome}",
            "Note_Content": f"Sentiment: {sentiment}\nTranscript:\n{transcript}"
        }
        # In a real implementation, this hits Zoho's Notes API
        # response = requests.post(f"{self.base_url}/Notes", headers=self.headers, json={"data": [note_payload]})
        return {"status": "success", "note_payload": note_payload}

    def sync_zoho_lead_to_local(self, zoho_lead_id):
        return {"status": "disabled"}

    def push_note(self, lead_id, title, content):
        db.log_action(lead_id, "zoho_note_disabled", title, "zoho_sync")
        return {"status": "disabled"}

    def push_activity(self, lead_id, activity_type, subject, details=None, duration=None, sentiment=None):
        db.log_action(lead_id, f"zoho_{activity_type}_disabled", subject, "zoho_sync")
        return {"status": "disabled"}

    def handle_webhook(self, event_data):
        return {"status": "disabled", "message": "Zoho integration is blank in this scaffold", "event": event_data}

    def convert_lead(self, lead_id, assign_to=None, create_deal=True, overwrite=False):
        db.log_action(lead_id, "zoho_convert_disabled", "Zoho integration is blank", "zoho_sync")
        return {"status": "disabled"}

    def sync_pending_local_leads(self, limit=50):
        return [{"status": "disabled"}]

    def weekly_analytics(self):
        total = db.count("SELECT COUNT(*) AS value FROM leads")
        converted = db.count("SELECT COUNT(*) AS value FROM leads WHERE outcome = 'converted'")
        pending = db.count("SELECT COUNT(*) AS value FROM leads WHERE status IN ('pending_approval', 'reviewed')")
        return {
            "total_leads": total,
            "converted": converted,
            "pending_review": pending,
            "conversion_rate": round((converted / total) * 100, 2) if total else 0,
        }

