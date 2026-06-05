import json
import os
import re
import urllib.error
import urllib.request


class SicadaCallAdapter:
    def __init__(self):
        self.api_key = os.environ.get("SICADA_API_KEY")
        self.agent_id = os.environ.get("SICADA_AGENT_ID")
        self.call_endpoint = os.environ.get("SICADA_CALL_ENDPOINT")
        self.auth_header = os.environ.get("SICADA_AUTH_HEADER", "Authorization")
        self.auth_scheme = os.environ.get("SICADA_AUTH_SCHEME", "Bearer")

    def configured(self):
        return bool(self.api_key and self.agent_id and self.call_endpoint)

    def call(self, lead):
        if not self.configured():
            raise ValueError(
                "Sicada is not configured. Set SICADA_API_KEY, SICADA_AGENT_ID, and SICADA_CALL_ENDPOINT."
            )
        number = normalize_phone(lead["phone"])
        payload = {
            "agent_id": self.agent_id,
            "customer": {
                "phone": number,
                "name": lead["name"],
            },
            "metadata": {
                "lead_id": str(lead["id"]),
                "lead_name": lead["name"],
                "lead_score": str(lead["score"]),
                "lead_priority": lead["priority"],
                "lead_source": lead["source"],
                "lead_notes": lead["notes"][:1000],
                "company": "Edysor.ai",
                "call_goal": "Understand what the customer needs and qualify the next step.",
            },
        }
        request = urllib.request.Request(
            self.call_endpoint,
            data=json.dumps(payload).encode(),
            headers={
                self.auth_header: self.auth_value(),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"Sicada call failed with HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Sicada call failed: {exc.reason}") from exc
        call_id = str(data.get("id") or data.get("call_id") or data.get("callId") or "")
        status = data.get("status", "queued")
        return {
            "outcome": "queued",
            "summary": f"Sicada outbound call created. status={status}, call_id={call_id}",
            "provider": "sicada",
            "provider_call_id": call_id,
            "raw_status": status,
        }

    def auth_value(self):
        if not self.auth_scheme:
            return self.api_key
        return f"{self.auth_scheme} {self.api_key}"


def normalize_phone(value):
    cleaned = re.sub(r"[^\d+]", "", value or "")
    if not cleaned.startswith("+"):
        raise ValueError("Sicada calls require an E.164 phone number, for example +919876543210.")
    if len(re.sub(r"\D", "", cleaned)) < 8:
        raise ValueError("Phone number is too short for an outbound call.")
    return cleaned
