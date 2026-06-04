import json
import os
import re
import urllib.error
import urllib.request


class VapiCallAdapter:
    def __init__(self):
        self.api_key = os.environ.get("VAPI_API_KEY")
        self.assistant_id = os.environ.get("VAPI_ASSISTANT_ID")
        self.phone_number_id = os.environ.get("VAPI_PHONE_NUMBER_ID")
        self.api_base = os.environ.get("VAPI_API_BASE", "https://api.vapi.ai")

    def configured(self):
        return bool(self.api_key and self.assistant_id and self.phone_number_id)

    def call(self, lead):
        if not self.configured():
            raise ValueError("Vapi is not configured. Set VAPI_API_KEY, VAPI_ASSISTANT_ID, and VAPI_PHONE_NUMBER_ID.")
        number = normalize_phone(lead["phone"])
        payload = {
            "phoneNumberId": self.phone_number_id,
            "assistantId": self.assistant_id,
            "customer": {
                "number": number,
                "name": lead["name"],
            },
            "assistantOverrides": {
                "variableValues": {
                    "lead_id": str(lead["id"]),
                    "lead_name": lead["name"],
                    "lead_score": str(lead["score"]),
                    "lead_priority": lead["priority"],
                    "lead_source": lead["source"],
                    "lead_notes": lead["notes"][:1000],
                }
            },
        }
        request = urllib.request.Request(
            f"{self.api_base}/call",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"Vapi call failed with HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Vapi call failed: {exc.reason}") from exc
        call_id = data.get("id", "")
        status = data.get("status", "queued")
        return {
            "outcome": "queued",
            "summary": f"Vapi outbound call created. status={status}, call_id={call_id}",
            "provider": "vapi",
            "provider_call_id": call_id,
            "raw_status": status,
        }


def normalize_phone(value):
    cleaned = re.sub(r"[^\d+]", "", value or "")
    if not cleaned.startswith("+"):
        raise ValueError("Vapi calls require an E.164 phone number, for example +14155550100.")
    if len(re.sub(r"\D", "", cleaned)) < 8:
        raise ValueError("Phone number is too short for a Vapi outbound call.")
    return cleaned
