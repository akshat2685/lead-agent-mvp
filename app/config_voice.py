import os

VOICE_AGENT_CONFIG = {
    "url": os.getenv("SCIDA_VOICE_AGENT_URL", ""),
    "api_key": os.getenv("SCIDA_VOICE_AGENT_KEY", ""),
    "queue_endpoint": "/api/queue/call",
    "callback_url": os.getenv("VOICE_CALLBACK_URL", ""),
}

