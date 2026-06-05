import os

from app import db
from app.adapters import GoogleSheetLeadAdapter, MockCrmAdapter, VoiceCallAdapter, import_zapier_lead
from app.scoring import action_reason, recommended_action, score_lead
from app.zoho_adapter import ZohoCrmAdapter


FOLLOW_UP_SECONDS = {
    "Hot": 2 * 60 * 60,
    "Warm": 6 * 60 * 60,
    "Nurture": 7 * 24 * 60 * 60,
    "Cold": 30 * 24 * 60 * 60,
}

ALLOWED_STATUSES = {
    "new",
    "open",
    "contacted",
    "follow_up",
    "qualified",
    "rejected",
    "not_relevant",
    "lost",
    "unresponsive",
    "needs_manual_contact",
    "calling",
}


def get_setting(key, default=None):
    found = db.row("select value from settings where key = ?", (key,))
    return found["value"] if found else default


def set_setting(key, value):
    db.execute(
        "insert into settings(key, value) values(?, ?) on conflict(key) do update set value=excluded.value",
        (key, value),
    )


def evaluate_leads():
    cleanup_dead_leads()
    try:
        zoho_imported = ZohoCrmAdapter().sync()
    except Exception as exc:
        db.event(None, "zoho_sync_error", str(exc))
        zoho_imported = 0
    try:
        sheet_imported = GoogleSheetLeadAdapter().sync()
    except Exception as exc:
        db.event(None, "sheet_sync_error", str(exc))
        sheet_imported = 0
    has_integration = bool(
        os.environ.get("GOOGLE_SHEET_URL")
        or os.environ.get("GOOGLE_SHEET_CSV_URL")
        or os.environ.get("ZAPIER_WEBHOOK_SECRET")
        or os.environ.get("ZOHO_REFRESH_TOKEN")
    )
    if not zoho_imported and not sheet_imported and (os.environ.get("ENABLE_DEMO_LEADS") == "true" or not has_integration):
        MockCrmAdapter().sync()
    leads = db.rows("select * from leads where status in ('new', 'open', 'follow_up')")
    created = 0
    for lead in leads:
        score, priority = score_lead(lead)
        db.execute(
            """
            update leads
            set score = ?,
                priority = ?,
                status = case when status = 'new' then 'open' else status end
            where id = ?
            """,
            (score, priority, lead["id"]),
        )
        updated = db.row("select * from leads where id = ?", (lead["id"],))
        created += queue_next_action(updated)
    return created


def queue_next_action(lead):
    action = recommended_action(lead)
    if action == "nurture":
        return 0
    existing = db.row(
        "select id from approvals where lead_id = ? and status = 'pending'",
        (lead["id"],),
    )
    if existing:
        db.execute(
            "update approvals set action = ?, reason = ? where id = ?",
            (action, action_reason(lead), existing["id"]),
        )
        return 0
    if get_setting("mode") == "autonomous":
        execute_action(lead, action)
        return 0
    db.execute(
        """
        insert into approvals(lead_id, action, reason, status, created_at)
        values(?, ?, ?, 'pending', ?)
        """,
        (lead["id"], action, action_reason(lead), db.now()),
    )
    return 1


def requeue_all_pending_actions():
    leads = db.rows("select * from leads where status in ('new', 'open', 'follow_up', 'needs_manual_contact')")
    updated = 0
    for lead in leads:
        score, priority = score_lead(lead)
        db.execute("update leads set score = ?, priority = ? where id = ?", (score, priority, lead["id"]))
        refreshed = db.row("select * from leads where id = ?", (lead["id"],))
        updated += queue_next_action(refreshed)
    return updated


def cleanup_dead_leads():
    dead = db.rows(
        """
        select * from leads
        where status in ('rejected', 'not_relevant', 'lost')
           or (status = 'unresponsive' and attempts >= 4)
        """
    )
    for lead in dead:
        tombstone = lead["external_id"] or lead["phone"]
        if tombstone:
            db.execute(
                """
                insert or replace into deleted_leads(key, reason, deleted_at)
                values(?, ?, ?)
                """,
                (tombstone, lead["status"], db.now()),
            )
        db.execute("delete from approvals where lead_id = ?", (lead["id"],))
        db.execute("delete from events where lead_id = ?", (lead["id"],))
        db.execute("delete from leads where id = ?", (lead["id"],))
    if dead:
        db.event(None, "cleanup", f"Deleted {len(dead)} dead leads.")
    return len(dead)


def score_and_queue_lead(lead_id):
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return None
    score, priority = score_lead(lead)
    db.execute(
        """
        update leads
        set score = ?,
            priority = ?,
            status = case when status = 'new' then 'open' else status end
        where id = ?
        """,
        (score, priority, lead_id),
    )
    updated = db.row("select * from leads where id = ?", (lead_id,))
    queue_next_action(updated)
    return db.row("select * from leads where id = ?", (lead_id,))


def receive_zapier_lead(payload):
    lead = import_zapier_lead(payload)
    return score_and_queue_lead(lead["id"])


def update_lead_status(payload):
    external_id = str(payload.get("external_id") or payload.get("id") or payload.get("url") or "").strip()
    phone = str(payload.get("phone") or payload.get("contact_info") or "").strip()
    status = str(payload.get("status") or "").strip().lower()
    if not status:
        raise ValueError("Missing status.")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported status: {status}.")
    lead = None
    if external_id:
        lead = db.row("select * from leads where external_id = ?", (external_id,))
    if not lead and phone:
        lead = db.row("select * from leads where phone = ?", (phone,))
    if not lead:
        raise ValueError("Lead not found.")
    db.execute("update leads set status = ? where id = ?", (status, lead["id"]))
    db.event(lead["id"], "zapier_status", f"Status set to {status} by Zapier.")
    return db.row("select * from leads where id = ?", (lead["id"],))


def set_lead_status(lead_id, status, source="telegram"):
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported status: {status}.")
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return None
    db.execute("update leads set status = ? where id = ?", (status, lead_id))
    if status in ("rejected", "not_relevant", "lost"):
        db.execute(
            "update approvals set status = 'rejected', decided_at = ? where lead_id = ? and status = 'pending'",
            (db.now(), lead_id),
        )
    db.event(lead_id, source, f"Status set to {status}.")
    return db.row("select * from leads where id = ?", (lead_id,))


def set_lead_phone(lead_id, phone):
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return None
    db.execute(
        "update leads set phone = ?, contact_status = 'has_phone', status = case when status = 'needs_manual_contact' then 'open' else status end where id = ?",
        (phone, lead_id),
    )
    db.event(lead_id, "telegram", "Phone/contact info updated.")
    return score_and_queue_lead(lead_id)


def research_done(lead_id):
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return None
    status = "open" if lead["contact_status"] == "has_phone" else "needs_manual_contact"
    db.execute("update leads set status = ? where id = ?", (status, lead_id))
    db.event(lead_id, "telegram", "Research marked done.")
    return score_and_queue_lead(lead_id)


def no_contact_found(lead_id):
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return None
    set_lead_status(lead_id, "not_relevant", source="telegram")
    cleanup_dead_leads()
    return lead


def reject_lead(lead_id):
    return set_lead_status(lead_id, "rejected")


def approve(approval_id):
    approval = db.row("select * from approvals where id = ?", (approval_id,))
    if not approval or approval["status"] != "pending":
        return False
    lead = db.row("select * from leads where id = ?", (approval["lead_id"],))
    db.execute(
        "update approvals set status = 'approved', decided_at = ? where id = ?",
        (db.now(), approval_id),
    )
    execute_action(lead, approval["action"])
    return True


def approve_research_lead(lead_id):
    approval = db.row(
        """
        select id from approvals
        where lead_id = ? and action = 'research_contact' and status = 'pending'
        order by created_at asc limit 1
        """,
        (lead_id,),
    )
    if not approval:
        return False
    return approve(approval["id"])


def approve_lead(lead_id):
    approval = db.row(
        "select id from approvals where lead_id = ? and status = 'pending' order by created_at asc limit 1",
        (lead_id,),
    )
    if not approval:
        return False
    return approve(approval["id"])


def reject(approval_id):
    approval = db.row(
        "select id from approvals where id = ? and status = 'pending'",
        (approval_id,),
    )
    if not approval:
        return False
    db.execute(
        "update approvals set status = 'rejected', decided_at = ? where id = ? and status = 'pending'",
        (db.now(), approval_id),
    )
    return True


def execute_due_actions():
    if get_setting("paused") == "true":
        return 0
    due = db.rows(
        "select * from leads where next_action_at is not null and next_action_at <= ?",
        (db.now(),),
    )
    count = 0
    for lead in due:
        if get_setting("mode") == "autonomous":
            execute_action(lead, "call")
        else:
            existing = db.row(
                "select id from approvals where lead_id = ? and status = 'pending'",
                (lead["id"],),
            )
            if not existing:
                db.execute(
                    """
                    insert into approvals(lead_id, action, reason, status, created_at)
                    values(?, 'call', ?, 'pending', ?)
                    """,
                    (lead["id"], f"Follow-up due for {lead['priority']} lead.", db.now()),
                )
        count += 1
    return count


def execute_action(lead, action):
    if action == "research_contact":
        db.execute(
            "update leads set status = 'needs_manual_contact' where id = ?",
            (lead["id"],),
        )
        db.event(lead["id"], "research_contact", "Lead needs contact info before outreach.")
        return
    if action != "call":
        return
    result = VoiceCallAdapter().call(lead)
    attempts = int(lead["attempts"]) + 1
    next_action = None
    status = "contacted"
    if result["outcome"] == "queued":
        status = "calling"
    elif result["outcome"] == "no_response" and attempts < 4:
        next_action = db.now() + FOLLOW_UP_SECONDS.get(lead["priority"], 86400)
        status = "follow_up"
    elif result["outcome"] == "no_response":
        status = "unresponsive"
    db.execute(
        """
        update leads
        set attempts = ?, last_action_at = ?, next_action_at = ?, status = ?
        where id = ?
        """,
        (attempts, db.now(), next_action, status, lead["id"]),
    )
    if result.get("provider_call_id"):
        db.execute(
            "update leads set active_call_id = ?, last_call_provider = ? where id = ?",
            (result["provider_call_id"], result.get("provider", "vapi"), lead["id"]),
        )
    db.event(lead["id"], "call", result["summary"])


def handle_vapi_webhook(payload):
    message = payload.get("message") or payload
    call = message.get("call") or {}
    call_id = call.get("id") or message.get("callId") or ""
    lead = find_lead_for_provider_call(call_id, "vapi", call)
    lead_id = lead["id"] if lead else None
    message_type = message.get("type", "unknown")
    status = message.get("status") or call.get("status") or ""
    ended_reason = message.get("endedReason") or call.get("endedReason") or ""
    artifact = message.get("artifact") or {}
    transcript = artifact.get("transcript") or ""
    summary = message.get("summary") or call.get("summary") or ""
    details = ", ".join(part for part in (status, ended_reason, summary) if part)
    db.event(lead_id, f"vapi_{message_type}", details or f"Received Vapi {message_type}.")
    if not lead:
        return {"ok": True, "matched": False}
    if message_type == "status-update":
        update_vapi_status(lead["id"], status)
    elif message_type == "end-of-call-report":
        final_status = final_vapi_status(ended_reason, transcript, summary)
        apply_call_final_status(lead, final_status)
        if transcript:
            db.event(lead["id"], "vapi_transcript", transcript[:1500])
    return {"ok": True, "matched": True}


def handle_sicada_webhook(payload):
    event = payload.get("event") or payload.get("type") or payload.get("status") or "unknown"
    call = payload.get("call") or payload.get("data") or payload
    call_id = (
        call.get("id")
        or call.get("call_id")
        or call.get("callId")
        or payload.get("call_id")
        or payload.get("callId")
        or ""
    )
    metadata = call.get("metadata") or payload.get("metadata") or {}
    lead = find_lead_for_provider_call(call_id, "sicada", {"metadata": metadata})
    lead_id = lead["id"] if lead else None
    raw_status = " ".join(
        str(part or "")
        for part in (
            event,
            call.get("status"),
            call.get("outcome"),
            call.get("ended_reason") or call.get("endedReason"),
            call.get("disposition"),
        )
    )
    transcript = (
        call.get("transcript")
        or payload.get("transcript")
        or ((call.get("artifact") or {}).get("transcript"))
        or ""
    )
    summary = (
        call.get("summary")
        or payload.get("summary")
        or call.get("call_summary")
        or payload.get("call_summary")
        or ""
    )
    details = ", ".join(part for part in (raw_status.strip(), summary) if part)
    db.event(lead_id, "sicada_webhook", details or "Received Sicada webhook.")
    if not lead:
        return {"ok": True, "matched": False}
    final_status = final_provider_status(raw_status, transcript, summary)
    apply_call_final_status(lead, final_status)
    if transcript:
        db.event(lead["id"], "sicada_transcript", transcript[:1500])
    if summary:
        db.event(lead["id"], "sicada_summary", summary[:1500])
    return {"ok": True, "matched": True, "status": final_status}


def find_lead_for_provider_call(call_id, provider, call):
    if call_id:
        lead = db.row(
            "select * from leads where active_call_id = ? and last_call_provider = ?",
            (call_id, provider),
        )
        if lead:
            return lead
    variables = (
        ((call.get("assistantOverrides") or {}).get("variableValues") or {})
        or call.get("metadata")
        or {}
    )
    lead_id = variables.get("lead_id")
    if lead_id:
        return db.row("select * from leads where id = ?", (lead_id,))
    return None


def update_vapi_status(lead_id, status):
    mapping = {
        "scheduled": "calling",
        "queued": "calling",
        "ringing": "calling",
        "in-progress": "calling",
        "ended": "contacted",
    }
    if status in mapping:
        db.execute("update leads set status = ? where id = ?", (mapping[status], lead_id))


def final_vapi_status(ended_reason, transcript, summary):
    return final_provider_status(ended_reason, transcript, summary)


def final_provider_status(reason_text, transcript, summary):
    reason = (reason_text or "").lower()
    failed_reasons = (
        "busy",
        "did-not-answer",
        "no-answer",
        "no_answer",
        "not_answered",
        "unanswered",
        "failed",
        "cancelled",
        "canceled",
        "voicemail",
        "invalid",
        "wrong",
    )
    if any(item in reason for item in failed_reasons):
        return "follow_up"
    if transcript or summary:
        return "contacted"
    return "follow_up"


def apply_call_final_status(lead, final_status):
    next_action = None
    status = final_status
    attempts = int(lead["attempts"])
    if final_status == "follow_up":
        if attempts < 4:
            next_action = db.now() + FOLLOW_UP_SECONDS.get(lead["priority"], 86400)
        else:
            status = "unresponsive"
    db.execute(
        """
        update leads
        set status = ?, next_action_at = ?, active_call_id = ''
        where id = ?
        """,
        (status, next_action, lead["id"]),
    )
