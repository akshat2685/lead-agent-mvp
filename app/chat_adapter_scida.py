import logging
import os

from . import db

logger = logging.getLogger(__name__)


class ScidaChatAdapter:
    """Placeholder chat adapter with no external connection."""

    def __init__(self, chat_endpoint=None, chat_api_key=None, base_url=None):
        self.chat_endpoint = chat_endpoint or os.getenv("SCIDA_CHAT_AGENT_URL", "")
        self.chat_api_key = chat_api_key or os.getenv("SCIDA_CHAT_AGENT_KEY", "")
        self.base_url = base_url or os.getenv("BASE_URL", "http://localhost:8765")

    def queue_outbound_message(self, lead_id, lead_data, channel="sms"):
        message_id = f"dry_run_chat_{lead_id}"
        db.log_action(lead_id, f"queued_for_chat_{channel}", f"Message ID: {message_id}", "chat_adapter")
        return message_id

    def handle_chat_webhook(self, event_data):
        lead_id = event_data.get("lead_id")
        if lead_id is not None:
            db.log_action(lead_id, f"chat_event_{event_data.get('event', 'unknown')}", "Webhook received", "chat_adapter")
        return {"status": "disabled", "message": "chat integration is blank in this scaffold"}
