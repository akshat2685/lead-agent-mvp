FIELD_MAP = {}


def split_name(full_name):
    full_name = (full_name or "").strip()
    if not full_name:
        return "", ""
    parts = full_name.split()
    if len(parts) == 1:
        return "", parts[0]
    return " ".join(parts[:-1]), parts[-1]


def build_lead_payload(lead):
    return {}


def build_note_payload(record_id, module_api_name, title, content):
    return {}


def build_task_payload(lead, subject, due_in_days=1):
    return {}


def build_call_payload(lead, subject, duration=None, sentiment=None):
    return {}


def build_deal_payload(lead, pipeline, stage, closing_days=30):
    return {}

