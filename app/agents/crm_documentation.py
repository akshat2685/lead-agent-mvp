import json
from pathlib import Path
from .llm_client import llm

class CRMDocumentationAgent:
    def __init__(self):
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "crm_documentation_agent.md"
        with open(prompt_path, "r") as f:
            self.system_prompt = f.read()

    def generate_record(self, interaction_data: dict) -> dict:
        user_prompt = f"Please convert the following interaction into a structured CRM record:\n\n{json.dumps(interaction_data, indent=2, default=str)}"
        return llm.call(self.system_prompt, user_prompt)
