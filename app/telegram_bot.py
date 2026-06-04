import json
import os
import re
import hashlib
import threading
import time
import urllib.parse
import urllib.request

from app import agent, db
from app.scoring import recommended_action_text, score_details
from app.web_research import analyze_lead_source, analyze_lead_source_result


ICONS = {
    "Hot": "🔥",
    "Warm": "🟠",
    "Nurture": "🟢",
    "Cold": "⚪",
}


def api(token, method, payload=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = None
    if payload:
        data = urllib.parse.urlencode(payload).encode()
    with urllib.request.urlopen(url, data=data, timeout=35) as res:
        return json.loads(res.read().decode())


def send(token, chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
    api(token, "sendMessage", payload)


def answer_callback(token, callback_id, text=""):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    api(token, "answerCallbackQuery", payload)


def handle(token, chat_id, text):
    text = text.strip()
    normalized = normalize_command(text)
    parts = normalized.split()
    cmd = parts[0].lower() if parts else ""
    if cmd in ("/start", "/help"):
        send(token, chat_id, start_message(), main_keyboard())
    elif cmd == "/status":
        pending = db.row("select count(*) c from approvals where status = 'pending'")["c"]
        hot = db.row("select count(*) c from leads where priority = 'Hot'")["c"]
        paused = agent.get_setting("paused", "false")
        send(token, chat_id, f"Status: {pending} pending approvals, {hot} hot leads, paused={paused}.")
    elif cmd == "/hot":
        leads = db.rows("select * from leads where priority = 'Hot' order by score desc limit 5")
        body = format_priority_leads("🔥 HOT LEADS", leads)
        send(token, chat_id, body)
    elif cmd == "/report":
        send(token, chat_id, daily_report())
    elif cmd == "/approvals":
        send_approval_cards(token, chat_id, "call")
    elif cmd == "/allapprovals":
        send(token, chat_id, approval_queue())
    elif cmd == "/sheet":
        send(token, chat_id, sheet_message())
    elif cmd == "/research":
        send_approval_cards(token, chat_id, "research_contact")
    elif cmd == "/approve" and len(parts) == 2:
        ok = agent.approve(int(parts[1]))
        send(token, chat_id, "Approved and executed." if ok else "Approval not found.")
    elif cmd == "/approvelead" and len(parts) == 2:
        ok = agent.approve_lead(int(parts[1]))
        send(token, chat_id, "Lead approval executed." if ok else "No pending approval for that lead.")
    elif cmd == "/approveresearch" and len(parts) == 2:
        ok = agent.approve_research_lead(int(parts[1]))
        send(token, chat_id, "Research task approved." if ok else "No pending research task for that lead.")
    elif cmd == "/researchdone" and len(parts) == 2:
        lead = agent.research_done(int(parts[1]))
        send(token, chat_id, f"Research done for lead #{lead['id']}." if lead else "Lead not found.")
    elif cmd == "/nocontact" and len(parts) == 2:
        lead = agent.no_contact_found(int(parts[1]))
        send(token, chat_id, f"No contact found. Lead #{lead['id']} will be removed from active queues." if lead else "Lead not found.")
    elif cmd == "/lead" and len(parts) == 2:
        lead_id = int(parts[1])
        send(token, chat_id, lead_detail(lead_id), lead_keyboard(lead_id))
    elif cmd == "/why" and len(parts) == 2:
        send(token, chat_id, lead_reason(int(parts[1])))
    elif cmd == "/analyze" and len(parts) == 2:
        send(token, chat_id, "Browsing source and analyzing lead. This can take a few seconds.")
        lead = db.row("select * from leads where id = ?", (int(parts[1]),))
        send_analysis_result(token, chat_id, lead)
    elif cmd == "/reject" and len(parts) == 2:
        lead = agent.reject_lead(int(parts[1]))
        send(token, chat_id, f"Rejected lead #{lead['id']} - {lead['name']}." if lead else "Lead not found.")
    elif cmd == "/mark" and len(parts) == 3:
        try:
            lead = agent.set_lead_status(int(parts[1]), parts[2])
            send(token, chat_id, f"Lead #{lead['id']} marked as {lead['status']}." if lead else "Lead not found.")
        except ValueError as exc:
            send(token, chat_id, str(exc))
    elif cmd == "/setphone" and len(parts) >= 3:
        lead = agent.set_lead_phone(int(parts[1]), " ".join(parts[2:]))
        send(token, chat_id, f"Lead #{lead['id']} contact updated." if lead else "Lead not found.")
    elif cmd == "/cleanup":
        deleted = agent.cleanup_dead_leads()
        send(token, chat_id, f"Deleted {deleted} dead leads.")
    elif cmd == "/pause":
        agent.set_setting("paused", "true")
        send(token, chat_id, "Agent paused.")
    elif cmd == "/resume":
        agent.set_setting("paused", "false")
        send(token, chat_id, "Agent resumed.")
    elif cmd == "/run":
        created = agent.evaluate_leads()
        send(token, chat_id, f"Scored leads and created {created} approval requests.")
    else:
        send(token, chat_id, fallback_message(), main_keyboard())


def handle_callback(token, callback):
    data = callback.get("data", "")
    callback_id = callback.get("id", "")
    message = callback.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id"))
    parts = data.split(":")
    action = parts[0] if parts else ""
    try:
        if action == "queue" and len(parts) == 2:
            send_approval_cards(token, chat_id, parts[1])
            answer_callback(token, callback_id)
        elif action == "lead" and len(parts) == 2:
            lead_id = int(parts[1])
            send(token, chat_id, lead_detail(lead_id), lead_keyboard(lead_id))
            answer_callback(token, callback_id)
        elif action == "source" and len(parts) == 2:
            send(token, chat_id, source_message(parts[1]))
            answer_callback(token, callback_id)
        elif action == "analyze" and len(parts) == 2:
            lead = db.row("select * from leads where id = ?", (int(parts[1]),))
            send(token, chat_id, "Browsing source and analyzing lead. This can take a few seconds.")
            send_analysis_result(token, chat_id, lead)
            answer_callback(token, callback_id)
        elif action == "applycontact" and len(parts) == 2:
            candidate = db.row("select * from research_candidates where token = ?", (parts[1],))
            if not candidate:
                send(token, chat_id, "Research candidate expired or not found.")
                answer_callback(token, callback_id)
                return
            lead_id = int(candidate["lead_id"])
            contact = candidate["contact"]
            lead = agent.set_lead_phone(lead_id, contact)
            send(token, chat_id, f"Applied contact to lead #{lead['id']}: {contact}" if lead else "Lead not found.")
            answer_callback(token, callback_id)
        elif action == "approve" and len(parts) == 2:
            ok = agent.approve(int(parts[1]))
            send(token, chat_id, "Approved and executed." if ok else "Approval not found.")
            answer_callback(token, callback_id)
        elif action == "approveresearch" and len(parts) == 2:
            ok = agent.approve_research_lead(int(parts[1]))
            send(token, chat_id, "Research task approved." if ok else "No pending research task for that lead.")
            answer_callback(token, callback_id)
        elif action == "rejectlead" and len(parts) == 2:
            lead = agent.reject_lead(int(parts[1]))
            send(token, chat_id, f"Rejected lead #{lead['id']} - {lead['name']}." if lead else "Lead not found.")
            answer_callback(token, callback_id)
        elif action == "phoneprompt" and len(parts) == 2:
            send(token, chat_id, f"Reply with: set phone for lead {parts[1]} +91...")
            answer_callback(token, callback_id)
        elif action == "researchdone" and len(parts) == 2:
            lead = agent.research_done(int(parts[1]))
            send(token, chat_id, f"Research done for lead #{lead['id']}." if lead else "Lead not found.")
            answer_callback(token, callback_id)
        elif action == "nocontact" and len(parts) == 2:
            lead = agent.no_contact_found(int(parts[1]))
            send(token, chat_id, f"No contact found. Lead #{lead['id']} removed from active queues." if lead else "Lead not found.")
            answer_callback(token, callback_id)
        else:
            answer_callback(token, callback_id, "Unsupported button.")
    except Exception as exc:
        send(token, chat_id, f"Button action failed: {exc}")
        answer_callback(token, callback_id)


def start_message():
    return "\n".join(
        [
            "Lead Agent is online.",
            "",
            "You can talk normally. Examples:",
            "- show hot leads",
            "- give me today's report",
            "- show pending approvals",
            "- show call approvals",
            "- send google sheet link",
            "- show research tasks",
            "- show lead 14",
            "- analyze lead 14",
            "- why is lead 14 hot?",
            "- approve 13",
            "- approve research for lead 14",
            "- research done for lead 14",
            "- no contact found for lead 14",
            "- reject lead 14",
            "- mark lead 14 as qualified",
            "- set phone for lead 14 +91...",
            "- delete dead leads",
            "- run scoring",
            "- pause the agent",
            "- resume outreach",
            "",
            "Commands also work: /status /hot /report /approvals /allapprovals /sheet /research /lead ID /analyze ID /why ID /approve ID /approveresearch ID /researchdone ID /nocontact ID /reject ID /mark ID status /setphone ID phone /cleanup /pause /resume /run",
        ]
    )


def fallback_message():
    return "\n".join(
        [
            "I can help with lead status, reports, approvals, and scoring.",
            "Try: show call approvals, show research tasks, set phone for lead 14 +91..., approve research for lead 14, delete dead leads, run scoring, pause, or resume.",
        ]
    )


def normalize_command(text):
    if not text:
        return ""
    lower = text.lower().strip()
    if lower.startswith("/"):
        return lower

    lead_id = extract_id(lower)
    if lead_id and any(phrase in lower for phrase in ("show lead", "lead detail", "details for lead", "open lead", "view lead")):
        return f"/lead {lead_id}"
    if lead_id and any(phrase in lower for phrase in ("analyze lead", "browse lead", "research lead", "analyze source", "browse source")):
        return f"/analyze {lead_id}"
    if lead_id and any(phrase in lower for phrase in ("research done", "done researching", "mark research done")):
        return f"/researchdone {lead_id}"
    if lead_id and any(phrase in lower for phrase in ("no contact found", "could not find contact", "no contact for lead")):
        return f"/nocontact {lead_id}"
    phone = extract_phone_update(lower)
    if lead_id and phone and any(phrase in lower for phrase in ("set phone", "add phone", "update phone", "contact found", "set contact")):
        return f"/setphone {lead_id} {phone}"
    if lead_id and any(phrase in lower for phrase in ("why", "reason", "explain")):
        return f"/why {lead_id}"
    if lead_id and any(phrase in lower for phrase in ("reject lead", "not relevant", "not useful", "ignore lead", "bad lead")):
        return f"/reject {lead_id}"
    status = extract_status(lower)
    if lead_id and status and any(phrase in lower for phrase in ("mark", "set", "status", "make lead")):
        return f"/mark {lead_id} {status}"

    approval_id = extract_id(lower)
    if approval_id and "research" in lower and any(word in lower for word in ("approve", "approved", "start", "do", "proceed")):
        return f"/approveresearch {approval_id}"
    if approval_id and "lead" in lower and any(word in lower for word in ("approve", "approved", "go ahead", "call", "proceed")):
        return f"/approvelead {approval_id}"
    if approval_id and any(word in lower for word in ("approve", "approved", "go ahead", "call", "proceed")):
        return f"/approve {approval_id}"

    if any(phrase in lower for phrase in ("start", "help", "what can you do", "how do i use")):
        return "/start"
    if any(phrase in lower for phrase in ("hot lead", "top lead", "priority lead", "best lead")):
        return "/hot"
    if any(phrase in lower for phrase in ("google sheet", "sheet link", "spreadsheet", "leads sheet")):
        return "/sheet"
    if any(phrase in lower for phrase in ("needs contact", "need contact", "contact info", "research queue", "not contactable", "research task")):
        return "/research"
    if any(phrase in lower for phrase in ("delete dead", "cleanup dead", "remove dead", "clean dead")):
        return "/cleanup"
    if any(phrase in lower for phrase in ("report", "summary", "daily update", "today update", "overview")):
        return "/report"
    if re.search(r"\ball approvals\b|\ball pending\b", lower):
        return "/allapprovals"
    if any(phrase in lower for phrase in ("call approval", "outreach approval", "approval", "pending", "waiting for me", "need approval")):
        return "/approvals"
    if any(phrase in lower for phrase in ("run", "sync", "score", "refresh", "pull leads", "fetch leads", "update leads")):
        return "/run"
    if any(phrase in lower for phrase in ("pause", "stop outreach", "hold outreach", "stop agent")):
        return "/pause"
    if any(phrase in lower for phrase in ("resume", "continue", "start outreach", "unpause")):
        return "/resume"
    if any(phrase in lower for phrase in ("status", "state", "are you running", "agent doing")):
        return "/status"
    return lower


def extract_id(text):
    match = re.search(r"(?:approval\s*)?#?(\d+)", text)
    return match.group(1) if match else None


def extract_status(text):
    status_phrases = {
        "not relevant": "not_relevant",
        "not_relevant": "not_relevant",
        "follow up": "follow_up",
        "follow-up": "follow_up",
        "qualified": "qualified",
        "contacted": "contacted",
        "rejected": "rejected",
        "lost": "lost",
        "unresponsive": "unresponsive",
        "open": "open",
        "new": "new",
    }
    for phrase, status in status_phrases.items():
        if phrase in text:
            return status
    return None


def extract_phone_update(text):
    match = re.search(r"(\+?\d[\d\s().-]{6,}\d)", text)
    return match.group(1).strip() if match else None


def sheet_message():
    url = os.environ.get("GOOGLE_SHEET_URL") or os.environ.get("GOOGLE_SHEET_CSV_URL")
    return f"Google Sheet:\n{url}" if url else "No Google Sheet URL is configured."


def approval_queue(action=None, title=None):
    params = []
    condition = "approvals.status = 'pending'"
    if action:
        condition += " and approvals.action = ?"
        params.append(action)
    approvals = db.rows(
        """
        select approvals.id, approvals.action, leads.id lead_id, leads.name,
               leads.score, leads.priority, leads.contact_status, approvals.reason
        from approvals join leads on leads.id = approvals.lead_id
        where """ + condition + """
        order by leads.score desc, approvals.created_at asc
        limit 10
        """,
        tuple(params),
    )
    if not approvals:
        return "No pending items in this queue."
    lines = [title or ("Call approvals" if action == "call" else "Pending approvals")]
    for item in approvals:
        label = "Research" if item["action"] == "research_contact" else "Approval"
        lines.append(f"{label} #{item['id']} | Lead #{item['lead_id']} | {item['name']}")
        lines.append(f"{item['priority']} {item['score']}/100 | {item['contact_status']}")
        lines.append(item["reason"])
        lines.append("")
    lines.append("")
    if action == "research_contact":
        lines.append("Use: show lead ID, set phone for lead ID +91..., or approve research for lead ID.")
    else:
        lines.append("Use: approve APPROVAL_ID or show lead ID.")
    return "\n".join(lines)


def send_approval_cards(token, chat_id, action):
    title = "Ready for outreach" if action == "call" else "Needs contact research"
    approvals = approval_items(action)
    if not approvals:
        send(token, chat_id, f"No pending items in {title.lower()}.", main_keyboard())
        return
    if action == "research_contact":
        top = approvals[0]
        send(token, chat_id, "Top research priority", main_keyboard())
        send(token, chat_id, approval_card_text(top), approval_keyboard(top))
        remaining = approvals[1:6]
        if remaining:
            send(token, chat_id, "Next research tasks")
        for item in remaining:
            send(token, chat_id, approval_card_text(item), approval_keyboard(item))
        return
    send(token, chat_id, title, main_keyboard())
    for item in approvals[:5]:
        text = approval_card_text(item)
        send(token, chat_id, text, approval_keyboard(item))


def approval_items(action):
    return db.rows(
        """
        select approvals.id, approvals.action, leads.id lead_id, leads.name,
               leads.score, leads.priority, leads.contact_status, approvals.reason
        from approvals join leads on leads.id = approvals.lead_id
        where approvals.status = 'pending' and approvals.action = ?
        order by leads.score desc, approvals.created_at asc
        limit 10
        """,
        (action,),
    )


def approval_card_text(item):
    label = "Call approval" if item["action"] == "call" else "Research task"
    return "\n".join(
        [
            f"{label} #{item['id']}",
            f"Lead #{item['lead_id']}: {item['name']}",
            f"{ICONS.get(item['priority'], '')} {item['priority']} ({item['score']}/100)",
            f"Contactability: {item['contact_status']}",
            "",
            item["reason"],
        ]
    )


def main_keyboard():
    return [
        [
            {"text": "Call Approvals", "callback_data": "queue:call"},
            {"text": "Research Tasks", "callback_data": "queue:research_contact"},
        ],
        [{"text": "Google Sheet", "callback_data": "source:sheet"}],
    ]


def approval_keyboard(item):
    lead_id = item["lead_id"]
    if item["action"] == "call":
        primary = {"text": "Approve Call", "callback_data": f"approve:{item['id']}"}
    else:
        primary = {"text": "Approve Research", "callback_data": f"approveresearch:{lead_id}"}
    return [
        [primary, {"text": "View Details", "callback_data": f"lead:{lead_id}"}],
        [
            {"text": "Open Source", "callback_data": f"source:{lead_id}"},
            {"text": "Analyze Source", "callback_data": f"analyze:{lead_id}"},
        ],
        [{"text": "Not Relevant", "callback_data": f"rejectlead:{lead_id}"}],
        [
            {"text": "Research Done", "callback_data": f"researchdone:{lead_id}"},
            {"text": "No Contact Found", "callback_data": f"nocontact:{lead_id}"},
        ] if item["action"] == "research_contact" else [],
    ]


def lead_keyboard(lead_id):
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return main_keyboard()
    buttons = [
        [
            {"text": "Open Source", "callback_data": f"source:{lead_id}"},
            {"text": "Analyze Source", "callback_data": f"analyze:{lead_id}"},
        ],
        [{"text": "Set Contact", "callback_data": f"phoneprompt:{lead_id}"}],
        [{"text": "Not Relevant", "callback_data": f"rejectlead:{lead_id}"}],
    ]
    pending = db.row(
        "select id, action from approvals where lead_id = ? and status = 'pending'",
        (lead_id,),
    )
    if pending and pending["action"] == "call":
        buttons.insert(0, [{"text": "Approve Call", "callback_data": f"approve:{pending['id']}"}])
    elif pending and pending["action"] == "research_contact":
        buttons.insert(0, [{"text": "Approve Research", "callback_data": f"approveresearch:{lead_id}"}])
        buttons.append(
            [
                {"text": "Research Done", "callback_data": f"researchdone:{lead_id}"},
                {"text": "No Contact Found", "callback_data": f"nocontact:{lead_id}"},
            ]
        )
    return [row for row in buttons if row]


def send_analysis_result(token, chat_id, lead):
    if not lead:
        send(token, chat_id, "Lead not found.")
        return
    result = analyze_lead_source_result(lead)
    keyboard = None
    if result["candidate"]:
        token_key = store_research_candidate(lead["id"], result["candidate"])
        keyboard = [
            [
                {"text": "Apply Contact", "callback_data": f"applycontact:{token_key}"},
                {"text": "Ignore", "callback_data": f"lead:{lead['id']}"},
            ],
            [{"text": "Open Source", "callback_data": f"source:{lead['id']}"}],
        ]
    send(token, chat_id, result["message"], keyboard)


def store_research_candidate(lead_id, contact):
    token_key = hashlib.sha1(f"{lead_id}:{contact}".encode()).hexdigest()[:16]
    db.execute(
        """
        insert or replace into research_candidates(token, lead_id, contact, created_at)
        values(?, ?, ?, ?)
        """,
        (token_key, lead_id, contact, db.now()),
    )
    return token_key


def source_message(lead_id):
    if str(lead_id) == "sheet":
        return sheet_message()
    lead = db.row("select * from leads where id = ?", (int(lead_id),))
    if not lead:
        return "Lead not found."
    source = lead["external_id"] or extract_url(lead["notes"])
    return f"Source for lead #{lead_id}:\n{source}" if source else "No source URL found for this lead."


def extract_url(text):
    match = re.search(r"https?://\S+|[A-Za-z0-9.-]+\.[A-Za-z]{2,}/\S*", text or "")
    return match.group(0) if match else ""


def lead_detail(lead_id):
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return "Lead not found."
    details = score_details(lead)
    reasons = "\n".join([f"- {reason}" for reason in details["reasons"]]) or "- No strong scoring signals"
    pending = db.row(
        "select id, action from approvals where lead_id = ? and status = 'pending'",
        (lead_id,),
    )
    approval_line = f"Pending approval: #{pending['id']} ({pending['action']})" if pending else "Pending approval: none"
    return "\n".join(
        [
            f"Lead #{lead['id']}: {lead['name']}",
            f"Priority: {ICONS.get(lead['priority'], '')} {lead['priority']} ({lead['score']}/100)",
            f"Status: {lead['status']}",
            f"Contactability: {lead['contact_status']}",
            f"Source: {lead['source']}",
            f"Contact: {lead['phone']}",
            approval_line,
            "",
            "Reason:",
            reasons,
            "",
            "Action:",
            recommended_action_text(lead),
            "",
            "Notes:",
            lead["notes"][:900] or "-",
        ]
    )


def lead_reason(lead_id):
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return "Lead not found."
    details = score_details(lead)
    reasons = "\n".join([f"- {reason}" for reason in details["reasons"]]) or "- No strong scoring signals"
    return "\n".join(
        [
            f"Lead #{lead['id']} scored {lead['score']}/100 and is {lead['priority']}.",
            "",
            "Scoring reasons:",
            reasons,
            "",
            f"Recommended action: {recommended_action_text(lead)}",
        ]
    )


def format_priority_leads(title, leads):
    if not leads:
        return "No hot leads yet."
    sections = [title]
    for index, lead in enumerate(leads, start=1):
        details = score_details(lead)
        reasons = "\n".join([f"- {reason}" for reason in details["reasons"]]) or "- No strong scoring signals"
        sections.append(
            "\n".join(
                [
                    f"{index}. {lead['name']}",
                    f"Score: {lead['score']}/100",
                    "Reason:",
                    reasons,
                    "",
                    "Action:",
                    recommended_action_text(lead),
                ]
            )
        )
    return "\n\n----------------\n\n".join(sections)


def daily_report():
    total = db.row("select count(*) c from leads")["c"]
    counts = {
        bucket: db.row("select count(*) c from leads where priority = ?", (bucket,))["c"]
        for bucket in ("Hot", "Warm", "Nurture", "Cold")
    }
    top = db.rows("select name, score from leads order by score desc limit 3")
    urgent = db.row(
        """
        select count(*) c from leads
        where priority = 'Hot'
        and attempts = 0
        and (last_action_at is null or last_action_at <= ?)
        """,
        (db.now() - 12 * 60 * 60,),
    )["c"]
    top_lines = "\n".join([f"{i}. {lead['name']} ({lead['score']})" for i, lead in enumerate(top, start=1)])
    return "\n".join(
        [
            "📊 Lead Summary",
            "",
            f"Total Leads: {total}",
            "",
            f"🔥 Hot: {counts['Hot']}",
            f"🟠 Warm: {counts['Warm']}",
            f"🟢 Nurture: {counts['Nurture']}",
            f"⚪ Cold: {counts['Cold']}",
            "",
            "Top Priority:",
            top_lines or "No leads yet.",
            "",
            "Urgent:",
            f"{urgent} Hot Leads have not been contacted for 12+ hours.",
        ]
    )


def run_polling(token, allowed_chat_id=None):
    offset = 0
    while True:
        try:
            result = api(token, "getUpdates", {"timeout": 20, "offset": offset})
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message") or {}
                callback = update.get("callback_query")
                if callback:
                    chat_id = str(((callback.get("message") or {}).get("chat") or {}).get("id"))
                    if allowed_chat_id and chat_id != str(allowed_chat_id):
                        continue
                    handle_callback(token, callback)
                    continue
                chat_id = str((msg.get("chat") or {}).get("id"))
                if allowed_chat_id and chat_id != str(allowed_chat_id):
                    continue
                handle(token, chat_id, msg.get("text", ""))
        except Exception as exc:
            print(f"telegram polling error: {exc}", flush=True)
            time.sleep(5)


def run_daily_report(token, chat_id, hour=9):
    sent_for_day = None
    while True:
        current = time.localtime()
        day_key = (current.tm_year, current.tm_yday)
        if current.tm_hour == hour and sent_for_day != day_key:
            try:
                send(token, chat_id, daily_report())
                sent_for_day = day_key
            except Exception as exc:
                print(f"telegram daily report error: {exc}", flush=True)
        time.sleep(60)


def start(token, allowed_chat_id=None):
    thread = threading.Thread(target=run_polling, args=(token, allowed_chat_id), daemon=True)
    thread.start()
    if allowed_chat_id:
        report_thread = threading.Thread(
            target=run_daily_report,
            args=(token, allowed_chat_id),
            daemon=True,
        )
        report_thread.start()
