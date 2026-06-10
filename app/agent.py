import logging
import re
from datetime import datetime

from . import db
from .chat_adapter_scida import ScidaChatAdapter
from .voice_adapter_scida import ScidaVoiceAdapter
from .agents import LeadOrchestrator, CRMDocumentationAgent, HumanEscalationEngine, FollowUpScheduler
from .agents.lead_scorer import LeadScorer
from .channels import ChannelRouter

logger = logging.getLogger(__name__)


def parse_lead_text(lead_text):
    data = {
        "raw_text": lead_text.strip(),
        "name": None,
        "phone": None,
        "email": None,
        "company": None,
        "source": "telegram",
        "intent": None,
        "engagement": None,
        "company_size": None,
    }
    patterns = {
        "name": r"(?:^|\n)\s*name\s*:\s*(.+)",
        "phone": r"(?:^|\n)\s*phone\s*:\s*(.+)",
        "email": r"(?:^|\n)\s*email\s*:\s*(.+)",
        "company": r"(?:^|\n)\s*company\s*:\s*(.+)",
        "source": r"(?:^|\n)\s*source\s*:\s*(.+)",
        "intent": r"(?:^|\n)\s*intent\s*:\s*(.+)",
        "engagement": r"(?:^|\n)\s*engagement\s*:\s*(.+)",
        "company_size": r"(?:^|\n)\s*company size\s*:\s*(.+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, lead_text, flags=re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip()
    return data


def normalize_value(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def calculate_score(lead_data):
    score = 0
    text = " ".join(
        [
            normalize_value(lead_data.get("name")) or "",
            normalize_value(lead_data.get("company")) or "",
            normalize_value(lead_data.get("raw_text")) or "",
        ]
    ).lower()
    if lead_data.get("email"):
        score += 20
    if lead_data.get("phone"):
        score += 20
    if lead_data.get("company"):
        score += 15
    if any(word in text for word in ("enterprise", "urgent", "demo", "buy", "budget")):
        score += 20
    if any(word in text for word in ("trial", "pricing", "quote", "decision maker")):
        score += 10
    if (lead_data.get("intent") or "").lower() in {"high", "urgent", "ready"}:
        score += 15
    return min(score, 100)


def bucket_for_score(score):
    if score >= 80:
        return "Hot"
    if score >= 60:
        return "Warm"
    if score >= 35:
        return "Nurture"
    return "Cold"


def lead_handler(lead_text):
    parsed = parse_lead_text(lead_text)
    duplicate = db.find_duplicate(parsed, parsed.get("source") or "telegram")
    payload = {
        "name": normalize_value(parsed.get("name")),
        "phone": normalize_value(parsed.get("phone")),
        "email": normalize_value(parsed.get("email")),
        "company": normalize_value(parsed.get("company")),
        "raw_text": normalize_value(parsed.get("raw_text")),
        "source": parsed.get("source") or "telegram",
        "source_timestamp": datetime.now(),
        "status": "duplicate" if duplicate else "new",
        "deduplicated_with_id": duplicate["id"] if duplicate else None,
        "intent": normalize_value(parsed.get("intent")),
        "engagement": normalize_value(parsed.get("engagement")),
        "company_size": normalize_value(parsed.get("company_size")),
    }
    lead_id = db.insert_lead(payload)
    if duplicate:
        db.log_action(
            lead_id,
            "duplicate_detected",
            f"Matches lead {duplicate['id']} from {duplicate['source']}",
            payload["source"],
        )
    else:
        db.log_action(lead_id, "created", f"Lead ingested from {payload['source']}", "system")
    payload["id"] = lead_id
    payload["lead_id"] = lead_id
    payload["duplicate"] = bool(duplicate)
    payload["duplicate_of"] = duplicate["id"] if duplicate else None
    return payload


def scoring_service(lead_data):
    if lead_data.get("duplicate"):
        lead_data.setdefault("bucket", "Cold")
        lead_data.setdefault("score", 0)
        return lead_data
    
    scorer = LeadScorer()
    return scorer.score_lead(lead_data)


def agent_orchestrator(lead_data):
    # Pass through Lead Orchestrator
    orchestrator = LeadOrchestrator()
    decision = orchestrator.determine_action(lead_data)
    
    lead_data["orchestrator_decision"] = decision
    lead_data["llm_summary"] = f"Action: {decision.get('action')}, Reason: {decision.get('reason')}"
    
    return lead_data


def request_approval(lead_id, score):
    db.update_lead(
        lead_id,
        {
            "status": "pending_approval",
            "scored_at": datetime.now(),
        },
    )
    db.log_action(lead_id, "approval_requested", f"Score: {score}", "system")


def scoring_engine(lead_data):
    if lead_data.get("duplicate"):
        response = (
            f"Lead {lead_data['id']} was marked as a duplicate of lead "
            f"{lead_data.get('duplicate_of')}. No outreach queued."
        )
        db.update_lead(lead_data["id"], {"response": response})
        return response

    lead_id = lead_data["lead_id"]
    score = lead_data.get("score", 0)
    bucket = lead_data.get("bucket") or bucket_for_score(score)
    summary = lead_data.get("llm_summary") or "Lead processed."

    if score >= 60:
        request_approval(lead_id, score)
    else:
        db.update_lead(
            lead_id,
            {
                "score": score,
                "bucket": bucket,
                "scored_at": datetime.now(),
                "status": "reviewed",
            },
        )
        db.log_action(lead_id, "reviewed", f"Bucket: {bucket}", "scoring_engine")

    response = (
        f"Lead {lead_id} processed.\n"
        f"Score: {score}\n"
        f"Bucket: {bucket}\n"
        f"{summary}"
    )
    db.update_lead(
        lead_id,
        {
            "response": response,
            "score": score,
            "bucket": bucket,
        },
    )
    return response


def approve_lead(lead_id, approved_by):
    db.update_lead(
        lead_id,
        {
            "status": "approved",
            "approved_at": datetime.now(),
            "approved_by": approved_by,
        },
    )
    db.log_action(lead_id, "approved", f"Approved by {approved_by}", approved_by)


def reject_lead(lead_id, rejected_by, reason=""):
    db.update_lead(
        lead_id,
        {
            "status": "rejected",
            "rejected_at": datetime.now(),
            "rejection_reason": reason,
        },
    )
    db.log_action(lead_id, "rejected", f"Reason: {reason}", rejected_by)


def queue_for_voice_call(lead_id):
    lead = db.query_lead(lead_id)
    if not lead:
        return {"error": "Lead not found"}
    if not lead.get("phone"):
        return {"error": "No phone number on file"}
    adapter = ScidaVoiceAdapter()
    call_id = adapter.initiate_call(lead_id, lead)
    db.update_lead(
        lead_id,
        {
            "status": "queued_for_voice",
            "assigned_channel": "voice",
            "call_queued_at": datetime.now(),
            "voice_call_id": call_id,
            "outreach_channel": "voice",
        },
    )
    return {"channel": "voice", "call_id": call_id}


def queue_for_chat(lead_id, channel="sms"):
    lead = db.query_lead(lead_id)
    if not lead:
        return {"error": "Lead not found"}
    if not lead.get("phone"):
        return {"error": "No phone number on file"}
    adapter = ScidaChatAdapter()
    message_id = adapter.queue_outbound_message(lead_id, lead, channel)
    db.update_lead(
        lead_id,
        {
            "status": f"queued_for_chat_{channel}",
            "assigned_channel": "chat",
            "chat_queued_at": datetime.now(),
            "chat_message_id": message_id,
            "outreach_channel": channel,
        },
    )
    return {"channel": "chat", "message_id": message_id}


def queue_nurture_sequence(lead_id):
    db.update_lead(
        lead_id,
        {
            "status": "queued_for_nurture",
            "assigned_channel": "nurture",
            "outreach_channel": "nurture",
        },
    )
    db.log_action(lead_id, "queued_for_nurture", "Automated nurture sequence", "system")
    return {"channel": "nurture", "status": "queued"}


def process_approved_lead(lead_id):
    lead = db.query_lead(lead_id)
    if not lead:
        return {"error": "Lead not found"}
        
    # 1. Lead Orchestrator
    orchestrator = LeadOrchestrator()
    orch_decision = orchestrator.determine_action(lead)
    action = orch_decision.get("action", "WAIT")
    
    # 2. Channel Router (If Action warrants outreach)
    result = {"channel": "none"}
    if action in ["CALL_NOW", "SCHEDULE_CALL", "SEND_WHATSAPP"]:
        approved = lead.get('status') == 'approved'
        result = ChannelRouter.route_and_send(lead, message_template="Hello from Edysor AI", approved=approved)
    else:
        result = queue_nurture_sequence(lead_id)

    # 4. CRM Update
    crm_agent = CRMDocumentationAgent()
    crm_update = crm_agent.generate_record(lead)
    
    # 5. Scheduler
    scheduler = FollowUpScheduler()
    schedule_decision = scheduler.schedule(lead)
    
    # 6. Human Escalation Check
    escalation_engine = HumanEscalationEngine()
    escalation_decision = escalation_engine.check_escalation(lead)
    
    # Update DB with all these AI decisions
    if "error" not in result:
        db.update_lead(
            lead_id,
            {
                "status": "assigned_for_outreach" if not escalation_decision.get("escalate") else "escalated",
                "assigned_channel": result.get("channel", "none"),
                "outreach_channel": result.get("channel", "none"),
            },
        )
        db.log_action(lead_id, "ai_orchestrated", 
            f"Action: {action}, Channel: {result.get('channel')}, Next Contact: {schedule_decision.get('next_contact_time')}", 
            "system")
            
        if escalation_decision.get("escalate"):
            db.log_action(lead_id, "escalated", escalation_decision.get("reason"), "human_escalation_engine")
            # This triggers Telegram Notification implicitly (if hooked up in bot)

    return result
