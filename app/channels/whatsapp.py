class WhatsAppChannel:
    def send(self, lead, message_template):
        # Call Twilio/Meta API
        return {"status": "sent", "channel": "whatsapp", "message_id": f"wa_{lead.get('id')}"}
        
    def status(self, message_id):
        return {"status": "delivered"}
        
    def webhook_handler(self, payload):
        return {"handled": True}
