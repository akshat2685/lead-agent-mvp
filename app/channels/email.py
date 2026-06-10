class EmailChannel:
    def send(self, lead, message_template):
        # Call SendGrid/Resend API
        return {"status": "sent", "channel": "email", "message_id": f"em_{lead.get('id')}"}
        
    def status(self, message_id):
        return {"status": "delivered"}
        
    def webhook_handler(self, payload):
        return {"handled": True}
