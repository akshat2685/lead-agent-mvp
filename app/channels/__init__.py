from .voice import VoiceChannel
from .whatsapp import WhatsAppChannel
from .email import EmailChannel
from .sms import SMSChannel
from ..agents.memory import MemoryEngine

class ChannelRouter:
    @staticmethod
    def route_and_send(lead, message_template, approved=True):
        score = lead.get('score', 0)
        lead_id = lead.get('id')
        
        # Inject Memory Context
        memory_summary = ""
        if lead_id:
            memory_engine = MemoryEngine()
            memory_summary = memory_engine.get_conversation_summary(lead_id)
            if memory_summary:
                message_template = f"Context: {memory_summary}\n\n{message_template}"
        
        if score >= 80 and approved:
            channel = VoiceChannel()
        elif score >= 60 and approved:
            channel = WhatsAppChannel()
        elif score >= 40:
            channel = EmailChannel()
        else:
            return {"status": "skipped", "reason": "Score too low or not approved"}
            
        return channel.send(lead, message_template)
