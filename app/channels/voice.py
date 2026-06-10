class VoiceChannel:
    def send(self, lead, message_template):
        # Call Vapi/Scida API
        return {"status": "sent", "channel": "voice", "message_id": f"voice_{lead.get('id')}"}
        
    def status(self, message_id):
        return {"status": "completed"}
        
    def webhook_handler(self, payload):
        return {"handled": True}
