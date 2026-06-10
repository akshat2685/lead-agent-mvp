import json
import os
from pathlib import Path
from .llm_client import llm

class LeadOrchestrator:
    def __init__(self):
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "lead_orchestrator.md"
        with open(prompt_path, "r") as f:
            self.system_prompt = f.read()

    def determine_action(self, lead_data: dict) -> dict:
        user_prompt = f"Please determine the next action for the following lead:\n\n{json.dumps(lead_data, indent=2, default=str)}"
        return llm.call(self.system_prompt, user_prompt)
