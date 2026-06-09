import logging
import os

from . import db

logger = logging.getLogger(__name__)


class ScidaVoiceAdapter:
    """Placeholder voice adapter with no external connection."""

    def __init__(self, voice_agent_endpoint=None, voice_agent_api_key=None, base_url=None):
        self.voice_agent_endpoint = voice_agent_endpoint or os.getenv("SCIDA_VOICE_AGENT_URL", "")
        self.voice_agent_api_key = voice_agent_api_key or os.getenv("SCIDA_VOICE_AGENT_KEY", "")
        self.base_url = base_url or os.getenv("BASE_URL", "http://localhost:8765")

    def initiate_call(self, lead_id, lead_data):
        call_id = f"dry_run_voice_{lead_id}"
        db.log_action(lead_id, "queued_for_voice", f"Call ID: {call_id}", "voice_adapter")
        return call_id

    def handle_call_webhook(self, event_data):
        lead_id = event_data.get("lead_id")
        if lead_id is not None:
            db.log_action(lead_id, f"voice_call_{event_data.get('outcome', 'unknown')}", "Webhook received", "voice_adapter")
        return {"status": "disabled", "message": "voice integration is blank in this scaffold"}
