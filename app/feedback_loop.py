from datetime import datetime

from . import db
from .zoho_sync import ZohoCRMService


def record_conversion(lead_id, outcome):
    lead = db.query_lead(lead_id)
    if not lead:
        return {"error": "Lead not found"}

    db.update_lead(
        lead_id,
        {
            "outcome": outcome,
            "outcome_date": datetime.now(),
        },
    )
    db.log_conversion(
        lead_id,
        lead.get("score"),
        lead.get("bucket"),
        outcome,
        {
            "intent": lead.get("intent"),
            "engagement": lead.get("engagement"),
            "company_size": lead.get("company_size"),
            "source": lead.get("source"),
            "days_to_contact": (datetime.now() - lead["created_at"]).days if lead.get("created_at") else None,
        },
    )
    service = ZohoCRMService()
    if service.enabled():
        try:
            service.push_note(lead_id, "Conversion outcome", f"Outcome recorded: {outcome}")
            if outcome == "converted":
                service.convert_lead(lead_id)
            db.update_lead(lead_id, {"zoho_sync_status": "conversion_recorded"})
        except Exception:
            pass
    return {"status": "recorded"}


def analyze_scoring_accuracy():
    rows = db.fetch_all(
        """
        SELECT
            bucket,
            COUNT(*) AS total,
            SUM(CASE WHEN outcome = 'converted' THEN 1 ELSE 0 END) AS converted,
            ROUND(100.0 * SUM(CASE WHEN outcome = 'converted' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS conversion_rate
        FROM leads
        WHERE outcome IS NOT NULL
          AND created_at > NOW() - INTERVAL '30 days'
        GROUP BY bucket
        ORDER BY bucket
        """
    )
    alerts = []
    for row in rows:
        if row["bucket"] == "Hot" and (row["conversion_rate"] or 0) < 30:
            alerts.append(f"Hot bucket only converting {row['conversion_rate']}%.")
        elif row["bucket"] == "Cold" and (row["conversion_rate"] or 0) > 60:
            alerts.append(f"Cold bucket converting {row['conversion_rate']}%.")
    return {"rows": rows, "alerts": alerts}
