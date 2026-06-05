import json
import os
import urllib.error
import urllib.request

from app import db


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


SYSTEM_PROMPT = """
You are the Telegram AI assistant for the Edysor.ai lead-calling system.

Your scope is specific:
- Sicada.ai setup and Priya voice agent operations
- Edysor.ai sales outreach, lead qualification, and follow-up workflows
- Google Sheet lead intake
- calling status, webhook setup, retries, summaries, and lead statuses
- practical sales conversations and objection handling for Edysor.ai

Behavior:
- Be concise, direct, and operational.
- If the user asks about something outside this scope, do not answer the outside topic. Say you are built for Edysor.ai's Sicada/Priya lead-calling workflow and offer to help with leads, calls, webhooks, retry logic, or sales follow-up.
- Do not invent API endpoints, pricing, legal claims, or Sicada features you have not been given.
- Never ask the user to paste API keys or auth tokens in chat. Tell them to put secrets in .env.
- When useful, mention exact local commands or Telegram commands.
- If a question needs live account access inside Sicada, say that clearly and tell the user what setting or screen to look for.
""".strip()


def configured():
    return bool(os.environ.get("OPENAI_API_KEY"))


def answer(user_text, chat_id=None):
    if not configured():
        return offline_answer()
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        "input": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_user_context(user_text, chat_id),
            },
        ],
        "max_output_tokens": int(os.environ.get("OPENAI_MAX_OUTPUT_TOKENS", "450")),
    }
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:400]
        return f"LLM request failed with HTTP {exc.code}: {body}"
    except urllib.error.URLError as exc:
        return f"LLM request failed: {exc.reason}"
    return extract_text(data) or "I could not produce a clear answer. Try asking about leads, Priya, Sicada, webhooks, or call follow-up logic."


def build_user_context(user_text, chat_id=None):
    context = {
        "user_message": user_text,
        "system_state": system_state(),
        "relevant_lead": relevant_lead(user_text),
    }
    if chat_id:
        context["telegram_chat_id"] = str(chat_id)
    return json.dumps(context, ensure_ascii=True)


def system_state():
    return {
        "company": "Edysor.ai",
        "voice_agent": "Priya",
        "voice_provider": os.environ.get("VOICE_PROVIDER", "mock"),
        "sicada_configured": bool(
            os.environ.get("SICADA_API_KEY")
            and os.environ.get("SICADA_AGENT_ID")
            and os.environ.get("SICADA_CALL_ENDPOINT")
        ),
        "google_sheet_configured": bool(os.environ.get("GOOGLE_SHEET_URL") or os.environ.get("GOOGLE_SHEET_CSV_URL")),
        "lead_counts": {
            "total": count("select count(*) c from leads"),
            "hot": count("select count(*) c from leads where priority = 'Hot'"),
            "calling": count("select count(*) c from leads where status = 'calling'"),
            "follow_up": count("select count(*) c from leads where status = 'follow_up'"),
            "pending_call_approvals": count(
                "select count(*) c from approvals where status = 'pending' and action = 'call'"
            ),
            "pending_research_tasks": count(
                "select count(*) c from approvals where status = 'pending' and action = 'research_contact'"
            ),
        },
        "available_telegram_commands": [
            "/status",
            "/voice",
            "/webhook",
            "/hot",
            "/report",
            "/approvals",
            "/research",
            "/lead ID",
            "/run",
            "/pause",
            "/resume",
        ],
    }


def relevant_lead(user_text):
    lead_id = extract_first_int(user_text)
    if not lead_id:
        return None
    lead = db.row("select * from leads where id = ?", (lead_id,))
    if not lead:
        return None
    return {
        "id": lead["id"],
        "name": lead["name"],
        "status": lead["status"],
        "priority": lead["priority"],
        "score": lead["score"],
        "attempts": lead["attempts"],
        "contact_status": lead["contact_status"],
        "source": lead["source"],
        "notes": lead["notes"][:500],
    }


def extract_first_int(text):
    digits = ""
    for char in text:
        if char.isdigit():
            digits += char
        elif digits:
            break
    return int(digits) if digits else None


def count(query):
    return db.row(query)["c"]


def extract_text(data):
    if data.get("output_text"):
        return data["output_text"].strip()
    chunks = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in ("output_text", "text"):
                text = content.get("text", "")
                if text:
                    chunks.append(text)
    return "\n".join(chunks).strip()


def offline_answer():
    return "\n".join(
        [
            "AI chat is not configured yet.",
            "",
            "Add this to .env:",
            "OPENAI_API_KEY=your_key",
            "OPENAI_MODEL=gpt-4.1-mini",
            "",
            "I can still handle commands like /status, /voice, /webhook, /approvals, /research, and /run.",
        ]
    )
