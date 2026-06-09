from .zoho_sync import ZohoCRMService


def handle_zoho_webhook(payload):
    service = ZohoCRMService()
    return service.handle_webhook(payload)

