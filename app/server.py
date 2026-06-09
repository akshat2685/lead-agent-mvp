import logging

try:
    from flask import Flask, jsonify, request
except ImportError as error:  # pragma: no cover - optional runtime dependency
    Flask = None
    flask_import_error = error

from . import db
from .agent import queue_for_chat, queue_for_voice_call
from .chat_adapter_scida import ScidaChatAdapter
from .voice_adapter_scida import ScidaVoiceAdapter
from .zoho_sync import ZohoCRMService

logger = logging.getLogger(__name__)


def create_app():
    if Flask is None:
        raise RuntimeError(f"Flask is required to run the API server: {flask_import_error}")

    app = Flask(__name__)

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
    def analytics_summary():
        service = ZohoCRMService()
        total_leads = db.count("SELECT COUNT(*) AS value FROM leads")
        by_bucket = db.fetch_all(
            """
            SELECT bucket, COUNT(*) AS count, ROUND(AVG(score), 0) AS avg_score
            FROM leads
            WHERE status <> 'rejected'
            GROUP BY bucket
            ORDER BY bucket
            """
        )
        new_leads = db.count(
            "SELECT COUNT(*) AS value FROM leads WHERE created_at > DATE_TRUNC('month', CURRENT_DATE)"
        )
        contacted = db.count(
            "SELECT COUNT(*) AS value FROM leads WHERE last_contact_date > DATE_TRUNC('month', CURRENT_DATE)"
        )
        converted = db.count(
            "SELECT COUNT(*) AS value FROM leads WHERE outcome = 'converted' AND outcome_date > DATE_TRUNC('month', CURRENT_DATE)"
        )
        return jsonify(
            {
                "total_leads": total_leads,
                "by_bucket": by_bucket,
                "this_month": {
                    "new_leads": new_leads,
                    "contacted": contacted,
                    "converted": converted,
                },
                "zoho": service.weekly_analytics(),
            }
        )

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=8765, debug=True)
