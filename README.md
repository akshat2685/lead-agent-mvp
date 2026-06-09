# Lead Agent MVP

This repository is a local agent scaffold.

It includes:

- lead ingestion
- deduplication
- scoring
- bucket routing
- Telegram interaction
- local audit history

It intentionally leaves external connections blank.

## Structure

```text
lead-agent-mvp/
  app/
    agent.py
    bot/
      telegram_handlers.py
    chat_adapter_scida.py
    db.py
    server.py
    voice_adapter_scida.py
    zoho_client.py
    zoho_mapper.py
    zoho_sync.py
    zoho_webhooks.py
```

## Run

```bash
pip install -r requirements.txt
python -m app.bot.telegram_handlers
```

Optional API server:

```bash
python -m app.server
```

## Environment

The `.env` file is included as a template with blank placeholders for the integrations.

Required local settings:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DB_HOST`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

Integration settings are intentionally blank:

- `SCIDA_VOICE_AGENT_URL`
- `SCIDA_VOICE_AGENT_KEY`
- `SCIDA_CHAT_AGENT_URL`
- `SCIDA_CHAT_AGENT_KEY`
- `ZOHO_ACCOUNTS_URL`
- `ZOHO_API_DOMAIN`
- `ZOHO_CLIENT_ID`
- `ZOHO_CLIENT_SECRET`
- `ZOHO_REFRESH_TOKEN`
- `ZOHO_ACCESS_TOKEN`

## Notes

- This repo is a scaffold, not a connected production deployment.
- The connection fields are left blank on purpose.
- Fill them only when you are ready to wire a real environment.

