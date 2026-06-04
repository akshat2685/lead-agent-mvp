# Lead Agent MVP

Lead scoring and outreach agent for Edysor-style admission leads. It can sync leads from Google Sheets or Zoho CRM, score them with the 0-100 priority framework, queue approvals in Telegram, show activity in a web dashboard, and place approved calls through either the local mock provider or Vapi.

## Current Safety Model

The agent runs in approval mode by default. It will recommend the next action and wait for Telegram or dashboard approval before calling a lead. Autonomous mode is intentionally gated behind `ALLOW_AUTONOMOUS=true` so the MVP can later be upgraded without changing the core flow.

## Run Locally

```bash
cp .env.example .env
python3 -m app.server
```

The server automatically loads `.env` from the project root. Environment variables already set by the host override values in `.env`.

The web dashboard runs on `http://127.0.0.1:8765` unless `PORT` is set.

## Required Production Environment

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_CHAT_ID=
GOOGLE_SHEET_URL=
SHEET_SYNC_INTERVAL_SECONDS=300
```

## Vapi Calling

Keep `VOICE_PROVIDER=mock` until the Vapi account is ready. To enable real outbound calls:

```bash
VOICE_PROVIDER=vapi
VAPI_API_KEY=
VAPI_ASSISTANT_ID=
VAPI_PHONE_NUMBER_ID=
VAPI_WEBHOOK_SECRET=
```

Configure the Vapi assistant/server URL to send webhooks to:

```text
https://YOUR_PUBLIC_DOMAIN/api/vapi/webhook?secret=YOUR_VAPI_WEBHOOK_SECRET
```

Enable Vapi server messages for `status-update` and `end-of-call-report`. The app stores Vapi call IDs on the lead, updates lead status while the call is in progress, and clears the active call when Vapi sends the final report.

Vapi expects phone numbers in E.164 format, for example `+14155550100`.

## Zoho CRM

Zoho is optional until credentials are available:

```bash
ZOHO_CLIENT_ID=
ZOHO_CLIENT_SECRET=
ZOHO_REFRESH_TOKEN=
ZOHO_ACCOUNTS_URL=https://accounts.zoho.com
ZOHO_API_BASE=https://www.zohoapis.com
```

## Health Check

```text
GET /health
GET /api/health
```

The health response shows whether Telegram, Google Sheets, Zoho, and Vapi are configured.
