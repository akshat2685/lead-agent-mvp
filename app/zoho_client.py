class ZohoCRMClient:
    """Blank Zoho client placeholder."""

    def __init__(self):
        self.enabled = False

    def create_record(self, module, records):
        return {"status": "disabled"}

    def update_record(self, module, record_id, fields):
        return {"status": "disabled"}

    def get_record(self, module, record_id):
        return {"status": "disabled"}

    def add_note(self, module, record_id, note_title, note_content):
        return {"status": "disabled"}

    def create_task(self, task_payload):
        return {"status": "disabled"}

    def create_call(self, call_payload):
        return {"status": "disabled"}

    def convert_lead(self, lead_id, payload):
        return {"status": "disabled"}

