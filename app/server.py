import logging

try:
    from flask import Flask, jsonify, request, render_template, make_response
except ImportError as error:  # pragma: no cover - optional runtime dependency
    Flask = None
    flask_import_error = error

from . import db
from .agent import queue_for_chat, queue_for_voice_call
from .chat_adapter_scida import ScidaChatAdapter
from .voice_adapter_scida import ScidaVoiceAdapter
from .zoho_sync import ZohoCRMService
from .auth import authenticate_user, create_initial_admin
from .middleware import require_auth, require_role

logger = logging.getLogger(__name__)


def create_app():
    if Flask is None:
        raise RuntimeError(f"Flask is required to run the API server: {flask_import_error}")

    app = Flask(__name__, template_folder='templates')
    
    # Initialize Admin User on startup
    with app.app_context():
        create_initial_admin()

    @app.route("/")
    def index():
        return render_template("login.html")
        
    @app.route("/login")
    def login_page():
        return render_template("login.html")
        
    @app.route("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.post("/api/login")
    def api_login():
        data = request.get_json(force=True, silent=False)
        auth_data = authenticate_user(data.get("email"), data.get("password"))
        if not auth_data:
            return jsonify({"error": "Invalid email or password"}), 401
        return jsonify(auth_data)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/voice/webhook")
    def voice_webhook():
        data = request.get_json(force=True, silent=False)
        adapter = ScidaVoiceAdapter()
        return jsonify(adapter.handle_call_webhook(data))

    @app.post("/api/chat/webhook")
    def chat_webhook():
        data = request.get_json(force=True, silent=False)
        adapter = ScidaChatAdapter()
        return jsonify(adapter.handle_chat_webhook(data))

    @app.post("/api/zoho/webhook")
    def zoho_webhook():
        data = request.get_json(force=True, silent=False)
        service = ZohoCRMService()
        return jsonify(service.handle_webhook(data))

    @app.post("/api/voice/queue")
    def voice_queue():
        data = request.get_json(force=True, silent=False)
        result = queue_for_voice_call(int(data["lead_id"]))
        return jsonify(result)

    @app.post("/api/chat/queue")
    def chat_queue():
        data = request.get_json(force=True, silent=False)
        result = queue_for_chat(int(data["lead_id"]), channel=data.get("channel", "sms"))
        return jsonify(result)

    @app.post("/api/zoho/sync")
    def zoho_sync():
        data = request.get_json(force=True, silent=False) if request.data else {}
        service = ZohoCRMService()
        if data.get("lead_id"):
            result = service.sync_local_lead_to_zoho(int(data["lead_id"]))
        else:
            result = {"results": service.sync_pending_local_leads()}
        return jsonify(result)

    @app.post("/api/zoho/lead/<int:lead_id>/convert")
    def zoho_convert_lead(lead_id):
        data = request.get_json(force=True, silent=False) if request.data else {}
        service = ZohoCRMService()
        result = service.convert_lead(
            lead_id,
            assign_to=data.get("assign_to"),
            create_deal=data.get("create_deal", True),
            overwrite=data.get("overwrite", False),
        )
        return jsonify(result)

    @app.get("/api/lead/<int:lead_id>/history")
    def lead_history(lead_id):
        rows = db.get_lead_history(lead_id)
        return jsonify(rows)

    @app.get("/api/analytics/summary")
    @require_role(["admin", "agent", "viewer"])
    def analytics_summary():
        # Mocking complex analytics for MVP
        data = {
            "funnel": {
                "Lead": 100,
                "Contacted": 80,
                "Qualified": 45,
                "Enrolled": 15
            },
            "channel_performance": {
                "voice": {"open_rate": 0.8, "reply_rate": 0.4},
                "whatsapp": {"open_rate": 0.95, "reply_rate": 0.6},
                "email": {"open_rate": 0.3, "reply_rate": 0.05}
            },
            "agent_productivity": {
                "actions_per_day": 34,
                "approval_rate": 0.85,
                "avg_response_time_minutes": 12
            },
            "source_attribution": {
                "Google Sheets": 40,
                "Zoho": 35,
                "Organic": 25
            }
        }
        return jsonify(data)

    @app.get("/api/analytics/export")
    @require_role(["admin", "agent", "viewer"])
    def analytics_export():
        csv_data = "Lead_ID,Name,Status,Score,Bucket,Channel\n1,Test Lead,Contacted,85,Hot,voice\n2,Another Lead,Qualified,90,Hot,whatsapp"
        output = make_response(csv_data)
        output.headers["Content-Disposition"] = "attachment; filename=analytics_export.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=8765, debug=True)
