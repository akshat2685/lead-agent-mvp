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
        db.update_lead(lead_id, {"zoho_sync_status": "disabled"})
        db.log_action(lead_id, "zoho_sync_disabled", "Zoho integration is blank in this scaffold", "zoho_sync")
        return {"status": "disabled"}

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

