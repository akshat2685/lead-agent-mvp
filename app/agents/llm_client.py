import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# Try to import openai, but fallback gracefully if not installed
try:
    from openai import OpenAI
    has_openai = True
except ImportError:
    has_openai = False


class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key and has_openai:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            if not self.api_key:
                logger.warning("OPENAI_API_KEY is not set. Using mock LLM client.")
            elif not has_openai:
                logger.warning("openai package is not installed. Using mock LLM client. Run: pip install openai")

    def call(self, system_prompt: str, user_prompt: str, require_json=True) -> dict:
        if not self.client:
            return self._mock_call(system_prompt, user_prompt)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"} if require_json else {"type": "text"},
                temperature=0.2
            )
            content = response.choices[0].message.content
            if require_json:
                return json.loads(content)
            return {"text": content}
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._mock_call(system_prompt, user_prompt)

    def _mock_call(self, system_prompt: str, user_prompt: str) -> dict:
        """Fallback mock for when no API key is present."""
        if "Lead Orchestrator" in system_prompt:
            return {"action": "CALL_NOW", "reason": "Mocked response", "priority": "high", "confidence": 0.8, "next_action_time": ""}
        if "Contact Strategy Engine" in system_prompt:
            return {"channel": "Voice Call", "reason": "Mocked response", "confidence": 0.8}
        if "Follow-Up Scheduler" in system_prompt:
            return {"next_contact_time": "2026-06-11T10:00:00Z", "reason": "Mocked response", "confidence": 0.8}
        if "CRM Documentation Agent" in system_prompt:
            return {"Lead status": "In Progress", "Interaction type": "Analysis", "Outcome": "Pending", "Customer sentiment": "Neutral", "Pain points": "Unknown", "Budget indicators": "Unknown", "Timeline indicators": "Unknown", "Next action": "CALL_NOW"}
        if "Human Escalation Engine" in system_prompt:
            return {"escalate": False, "reason": "Mocked response", "recommended_human_action": ""}
        return {"response": "Mocked generic response"}

llm = LLMClient()
