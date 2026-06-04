INTENT_SCORE = {
    "requested_demo": (40, "Requested demo"),
    "booked_meeting": (40, "Booked meeting"),
    "asked_pricing": (35, "Asked pricing"),
    "replied_email": (20, "Replied to email"),
    "downloaded_brochure": (15, "Downloaded brochure"),
    "website_visit": (5, "Website visit only"),
}

ORG_SCORE = {
    "large_university": (25, "Large university"),
    "medium_university": (20, "Medium university"),
    "college_group": (15, "College group"),
    "training_institute": (10, "Training institute"),
}

ENGAGEMENT_SCORE = {
    "today": (20, "Active today"),
    "within_3_days": (15, "Active within 3 days"),
    "within_7_days": (10, "Active within 7 days"),
    "stale_30_days": (0, "No activity for 30+ days"),
}

FIT_SCORE = {
    "high_inquiry_volume": (15, "High inquiry volume"),
    "manual_admissions": (15, "Manual admissions process"),
    "moderate_fit": (8, "Moderate Edysor fit"),
    "advanced_ai": (3, "Already using advanced AI automation"),
}


def _score_part(lead, field, table):
    value = lead.get(field) or ""
    points, reason = table.get(value, (0, None))
    return points, reason


def score_details(lead):
    score = 0
    reasons = []
    for field, table in (
        ("intent", INTENT_SCORE),
        ("prospect_type", ORG_SCORE),
        ("engagement", ENGAGEMENT_SCORE),
        ("fit", FIT_SCORE),
    ):
        points, reason = _score_part(lead, field, table)
        score += points
        if reason and points > 0:
            reasons.append(reason)

    score = max(0, min(score, 100))
    if score >= 80:
        priority = "Hot"
    elif score >= 60:
        priority = "Warm"
    elif score >= 40:
        priority = "Nurture"
    else:
        priority = "Cold"
    return {"score": score, "priority": priority, "reasons": reasons}


def score_lead(lead):
    details = score_details(lead)
    return details["score"], details["priority"]


def recommended_action(lead):
    if lead.get("contact_status") != "has_phone":
        return "research_contact"
    if lead["priority"] == "Hot":
        return "call"
    if lead["priority"] == "Warm":
        return "call"
    return "nurture"


def recommended_action_text(lead):
    if lead.get("contact_status") == "has_url_only":
        return "Open source URL and identify contact info"
    if lead.get("contact_status") in ("needs_manual_contact", "not_contactable", "unknown"):
        return "Research contact info before outreach"
    if lead["priority"] == "Hot":
        return "Call within 1 hour"
    if lead["priority"] == "Warm":
        return "Follow up today"
    if lead["priority"] == "Nurture":
        return "Start education sequence and follow up weekly"
    return "Keep in CRM and automate light touchpoints"


def action_reason(lead):
    details = score_details(lead)
    reasons = ", ".join(details["reasons"]) or "No strong scoring signals"
    return f"{lead['priority']} lead scored {lead['score']}/100: {reasons}."
