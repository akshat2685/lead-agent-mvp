# Lead Agent MVP

This repository is a self-serve AI agent scaffold.

Someone cloning this repo should immediately see:

- the agent entrypoint
- the local data layer
- the Telegram bot interface
- blank integration adapters
- a clear environment template
- the files they need to customize for their own agent

## What It Does

- Ingests lead text from Telegram
- Deduplicates leads by email and phone
- Scores leads with local rules
- Buckets leads into hot, warm, nurture, or cold
- Tracks audit history in PostgreSQL
- Provides blank integration surfaces for voice, chat, and CRM sync

## Files To Customize

If someone wants their own version of this agent, these are the main files to edit:

- [`app/agent.py`](app/agent.py) - scoring, routing, and agent behavior
- [`app/db.py`](app/db.py) - schema and local persistence
- [`app/bot/telegram_handlers.py`](app/bot/telegram_handlers.py) - Telegram commands and operator flow
- [`app/server.py`](app/server.py) - HTTP endpoints and webhooks
- [`app/voice_adapter_scida.py`](app/voice_adapter_scida.py) - voice adapter placeholder
- [`app/chat_adapter_scida.py`](app/chat_adapter_scida.py) - chat adapter placeholder
- [`app/zoho_sync.py`](app/zoho_sync.py) - CRM sync placeholder

## Project Structure

```text
lead-agent-mvp/
  .env.example
  README.md
  requirements.txt
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

## Quick Start

1. Clone the repo.
2. Copy `.env.example` to `.env`.
3. Fill in the values you need.
4. Install dependencies.
5. Start the bot or the API server.

```bash
pip install -r requirements.txt
python -m app.bot.telegram_handlers
```

Optional API server:

```bash
python -m app.server
```

## Environment Setup

This repo includes [`.env.example`](.env.example) as the tracked template.

Copy it to `.env` before running the app:

```bash
copy .env.example .env
```

### Required Local Settings

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DB_HOST`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

### Optional Integration Settings

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

### Optional Runtime Settings

- `ZOHO_API_VERSION`
- `ZOHO_REDIRECT_URI`
- `ZOHO_DEFAULT_OWNER_ID`
- `ZOHO_DEAL_PIPELINE`
- `ZOHO_DEAL_STAGE`
- `ZOHO_REVIEW_THRESHOLD`
- `BASE_URL`

## For Your Own Agent

If you want to make this repo your own:

- replace the brand names and labels in the README
- tune the scoring rules in `app/agent.py`
- change the local database schema in `app/db.py`
- wire your own webhook integrations in the adapter files
- add or remove Telegram commands in `app/bot/telegram_handlers.py`

## Notes

- The integration files are intentionally blank placeholders.
- The repo is usable without external services.
- `.env` should stay uncommitted.
- `.env.example` is the file other people should copy and fill in.
