import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import agent, db, telegram_bot


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def json_response(handler, status, payload):
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_post_payload(handler):
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length).decode() if length else ""
    content_type = handler.headers.get("Content-Type", "")
    if "application/json" in content_type and raw:
        return json.loads(raw)
    parsed = parse_qs(raw)
    return {key: values[-1] for key, values in parsed.items()}


def zapier_authorized(params):
    secret = os.environ.get("ZAPIER_WEBHOOK_SECRET")
    if not secret:
        return True
    return params.get("secret", [""])[0] == secret


def vapi_authorized(params, handler):
    secret = os.environ.get("VAPI_WEBHOOK_SECRET")
    if not secret:
        return True
    header = handler.headers.get("X-Vapi-Secret", "")
    return header == secret or params.get("secret", [""])[0] == secret


def state():
    return {
        "settings": {
            "mode": agent.get_setting("mode", "approval"),
            "paused": agent.get_setting("paused", "false"),
        },
        "leads": db.rows("select * from leads order by score desc, id asc"),
        "approvals": db.rows(
            """
            select approvals.*, leads.name lead_name, leads.score lead_score, leads.priority lead_priority
            from approvals join leads on leads.id = approvals.lead_id
            order by approvals.created_at desc
            """
        ),
        "events": db.rows("select * from events order by created_at desc limit 50"),
    }


def health_state():
    return {
        "ok": True,
        "mode": agent.get_setting("mode", "approval"),
        "voice_provider": os.environ.get("VOICE_PROVIDER", "mock"),
        "vapi_configured": bool(
            os.environ.get("VAPI_API_KEY")
            and os.environ.get("VAPI_ASSISTANT_ID")
            and os.environ.get("VAPI_PHONE_NUMBER_ID")
        ),
        "sheet_configured": bool(os.environ.get("GOOGLE_SHEET_URL") or os.environ.get("GOOGLE_SHEET_CSV_URL")),
        "zoho_configured": bool(os.environ.get("ZOHO_REFRESH_TOKEN")),
        "telegram_configured": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/health", "/api/health"):
            json_response(self, 200, health_state())
            return
        if parsed.path == "/api/state":
            json_response(self, 200, state())
            return
        path = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
        target = (WEB / path).resolve()
        if not str(target).startswith(str(WEB.resolve())) or not target.exists():
            self.send_error(404)
            return
        content_type = "text/html"
        if target.suffix == ".css":
            content_type = "text/css"
        elif target.suffix == ".js":
            content_type = "application/javascript"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/api/agent/run":
            created = agent.evaluate_leads()
            json_response(self, 200, {"created_approvals": created})
        elif parsed.path == "/api/zapier/lead":
            if not zapier_authorized(params):
                json_response(self, 401, {"ok": False, "error": "Unauthorized"})
                return
            try:
                lead = agent.receive_zapier_lead(read_post_payload(self))
                json_response(self, 200, {"ok": True, "lead": lead})
            except Exception as exc:
                json_response(self, 400, {"ok": False, "error": str(exc)})
        elif parsed.path == "/api/zapier/status":
            if not zapier_authorized(params):
                json_response(self, 401, {"ok": False, "error": "Unauthorized"})
                return
            try:
                lead = agent.update_lead_status(read_post_payload(self))
                json_response(self, 200, {"ok": True, "lead": lead})
            except Exception as exc:
                json_response(self, 400, {"ok": False, "error": str(exc)})
        elif parsed.path == "/api/vapi/webhook":
            if not vapi_authorized(params, self):
                json_response(self, 401, {"ok": False, "error": "Unauthorized"})
                return
            try:
                result = agent.handle_vapi_webhook(read_post_payload(self))
                json_response(self, 200, result)
            except Exception as exc:
                json_response(self, 400, {"ok": False, "error": str(exc)})
        elif parsed.path.startswith("/api/approvals/") and parsed.path.endswith("/approve"):
            approval_id = int(parsed.path.split("/")[3])
            json_response(self, 200, {"ok": agent.approve(approval_id)})
        elif parsed.path.startswith("/api/approvals/") and parsed.path.endswith("/reject"):
            approval_id = int(parsed.path.split("/")[3])
            json_response(self, 200, {"ok": agent.reject(approval_id)})
        elif parsed.path == "/api/settings":
            if "paused" in params:
                agent.set_setting("paused", params["paused"][0])
            if "mode" in params and params["mode"][0] in ("approval", "autonomous"):
                if params["mode"][0] == "autonomous" and os.environ.get("ALLOW_AUTONOMOUS") != "true":
                    json_response(self, 403, {"ok": False, "error": "Autonomous mode is disabled for this MVP."})
                    return
                agent.set_setting("mode", params["mode"][0])
            json_response(self, 200, {"ok": True, "settings": state()["settings"]})
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)


def scheduler_loop():
    last_sync = 0
    while True:
        try:
            if agent.get_setting("paused", "false") != "true":
                agent.execute_due_actions()
                interval = int(os.environ.get("SHEET_SYNC_INTERVAL_SECONDS", "300"))
                has_sheet = os.environ.get("GOOGLE_SHEET_URL") or os.environ.get("GOOGLE_SHEET_CSV_URL")
                if has_sheet and time.time() - last_sync >= interval:
                    agent.evaluate_leads()
                    last_sync = time.time()
        except Exception as exc:
            print(f"scheduler error: {exc}", flush=True)
        time.sleep(30)


def main():
    db.init_db()
    agent.cleanup_dead_leads()
    if os.environ.get("ENABLE_DEMO_LEADS") == "true":
        db.seed_demo_leads()
    agent.evaluate_leads()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        telegram_bot.start(token, os.environ.get("TELEGRAM_ALLOWED_CHAT_ID"))
    threading.Thread(target=scheduler_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8765"))
    print(f"Lead agent MVP running at http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
