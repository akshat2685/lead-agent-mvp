import os

CHAT_AGENT_CONFIG = {
    "url": os.getenv("SCIDA_CHAT_AGENT_URL", ""),
    "api_key": os.getenv("SCIDA_CHAT_AGENT_KEY", ""),
    "queue_endpoint": "/api/queue/message",
    "callback_url": os.getenv("CHAT_CALLBACK_URL", ""),
}

