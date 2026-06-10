import json
from pathlib import Path
from .llm_client import llm

class HumanEscalationEngine:
    def __init__(self):
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "human_escalation_engine.md"
        with open(prompt_path, "r") as f:
            self.system_prompt = f.read()

    def check_escalation(self, lead_data: dict) -> dict:
        user_prompt = f"Please determine whether human intervention is required for this lead:\n\n{json.dumps(lead_data, indent=2, default=str)}"
        return llm.call(self.system_prompt, user_prompt)
