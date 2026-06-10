from ..db import get_session
from ..models import Conversation
from .llm_client import llm

class MemoryEngine:
    def get_conversation_summary(self, lead_id: int) -> str:
        session = get_session()
        try:
            conversations = session.query(Conversation).filter(
                Conversation.lead_id == lead_id
            ).order_by(Conversation.timestamp.desc()).limit(3).all()
            
            if not conversations:
                return ""
                
            history_text = "\n".join([f"[{c.timestamp.date()}] ({c.channel}): {c.content}" for c in reversed(conversations)])
            
            prompt = f"Summarize these recent interactions into a 1-sentence context for a sales agent.\n\n{history_text}"
            summary = llm.call(prompt, "Summarize the interaction.", require_json=False)
            
            # The LLM Client currently returns a JSON payload by default if it's the mock,
            # or a string if it's real. Let's handle both.
            if isinstance(summary, dict):
                return summary.get("text", "Previous calls discussed interest.")
            return str(summary)
        finally:
            session.close()

    def log_interaction(self, lead_id: int, channel: str, content: str):
        session = get_session()
        try:
            conversation = Conversation(lead_id=lead_id, channel=channel, content=content)
            session.add(conversation)
            session.commit()
        finally:
            session.close()
