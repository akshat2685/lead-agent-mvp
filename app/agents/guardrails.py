import os
import pytz
from datetime import datetime, timedelta
from ..db import get_session
from ..models import LeadHistory

ALLOW_AUTONOMOUS = os.getenv("ALLOW_AUTONOMOUS", "false").lower() == "true"
MAX_ACTIONS_PER_DAY = 50
BLACKLIST = {"do_not_call", "opt_out"}

class GuardrailEngine:
    def __init__(self):
        # We store autonomous states in memory or DB depending on deployment.
        # For MVP, we'll check the DB directly.
        pass

    def check_guardrails(self, lead_data: dict) -> dict:
        if not ALLOW_AUTONOMOUS:
            return {"allow": False, "reason": "ALLOW_AUTONOMOUS is disabled"}

        # 1. Emergency Stop Check
        if os.getenv("EMERGENCY_STOP_ACTIVE", "false").lower() == "true":
            return {"allow": False, "reason": "Emergency stop is active"}

        # 2. Blacklist Check
        status = lead_data.get("status", "")
        if status in BLACKLIST:
            return {"allow": False, "reason": "Lead is on blacklist"}

        # 3. Time Window Check (9 AM - 7 PM local time)
        # Assuming server time or lead timezone (defaulting to UTC for this scaffold)
        current_hour = datetime.utcnow().hour
        if current_hour < 9 or current_hour >= 19:
            return {"allow": False, "reason": "Outside business hours (9 AM - 7 PM)"}

        # 4. Daily Spend Cap (Max 50 actions/day)
        session = get_session()
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            actions_today = session.query(LeadHistory).filter(
                LeadHistory.changed_by == "autonomous_agent",
                LeadHistory.timestamp >= today_start
            ).count()
            if actions_today >= MAX_ACTIONS_PER_DAY:
                return {"allow": False, "reason": f"Daily action cap ({MAX_ACTIONS_PER_DAY}) reached"}

            # 5. Consecutive Failure Check (3 failures)
            recent_failures = session.query(LeadHistory).filter(
                LeadHistory.action == "autonomous_failure"
            ).order_by(LeadHistory.timestamp.desc()).limit(3).all()
            
            if len(recent_failures) == 3:
                return {"allow": False, "reason": "Paused due to 3 consecutive failures"}
                
        finally:
            session.close()

        return {"allow": True, "reason": "Guardrails passed"}

    def log_autonomous_action(self, lead_id: int, action: str, reason: str):
        session = get_session()
        try:
            history = LeadHistory(
                lead_id=lead_id, 
                action=action, 
                notes=reason, 
                changed_by="autonomous_agent"
            )
            session.add(history)
            session.commit()
        finally:
            session.close()
