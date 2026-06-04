# Lead Agent MVP 🚀

A lead scoring and outreach assistant for admission and education sales teams. It collects leads from Google Sheets or Zoho CRM, scores them from 0-100, sends priority alerts to Telegram, shows a live web dashboard, and can place approved outbound calls through Vapi.

The project starts in approval mode, so calls are not made until a human approves them from Telegram or the dashboard. A path for autonomous mode is already present, but it is locked behind an environment flag.

## What It Does ✨

- Scores every lead using a 0-100 priority framework
- Groups leads into Hot, Warm, Nurture, and Cold buckets
- Sends Telegram reports and approval buttons
- Reads leads from Google Sheets
- Includes a Zoho CRM connector
- Supports Vapi outbound phone calls
- Tracks call status through Vapi webhooks
- Shows leads, approvals, and activity in a web dashboard
- Cleans up dead or rejected leads
- Loads credentials from a local `.env` file

## Tools Used 🧰

- Python standard library for the backend server
- SQLite for local lead storage
- Telegram Bot API for bot controls and approval buttons
- Google Sheets published CSV for lead import
- Zoho CRM API for direct CRM sync
- Vapi API for outbound voice calls
- HTML, CSS, and JavaScript for the dashboard
- GitHub for version control and deployment handoff

## Project Structure 📁

```text
app/
  agent.py           Lead scoring, approvals, actions, and status updates
  adapters.py        Google Sheet import and call provider routing
  db.py              SQLite schema and migrations
  env_loader.py      Loads .env values without extra dependencies
  server.py          Web server, API routes, scheduler, and webhooks
  telegram_bot.py    Telegram commands, buttons, and reports
  vapi_adapter.py    Vapi outbound calling
  zoho_adapter.py    Zoho CRM sync
web/
  index.html         Dashboard
  style.css          Dashboard styling
  app.js             Dashboard behavior
tests/
  test_env_loader.py
  test_vapi.py
```

## Quick Start ⚡

```bash
git clone https://github.com/akshat2685/lead-agent-mvp.git
cd lead-agent-mvp
cp .env.example .env
python3 -m app.server
```

Open the dashboard:

```text
http://127.0.0.1:8765
```

The server automatically loads `.env` from the project root. Values already set in the machine or hosting platform override `.env`.

## Environment Variables 🔐

Create your local `.env` from `.env.example`:

```bash
cp .env.example .env
```

Fill only your own credentials:

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_CHAT_ID=
GOOGLE_SHEET_URL=
SHEET_SYNC_INTERVAL_SECONDS=300
ZAPIER_WEBHOOK_SECRET=

ZOHO_CLIENT_ID=
ZOHO_CLIENT_SECRET=
ZOHO_REFRESH_TOKEN=
ZOHO_ACCOUNTS_URL=https://accounts.zoho.com
ZOHO_API_BASE=https://www.zohoapis.com
ZOHO_MODULE=Leads
ZOHO_PER_PAGE=100

VOICE_PROVIDER=mock
VAPI_API_KEY=
VAPI_ASSISTANT_ID=
VAPI_PHONE_NUMBER_ID=
VAPI_API_BASE=https://api.vapi.ai
VAPI_WEBHOOK_SECRET=
```

Never commit `.env`. It is already ignored by `.gitignore`.

## How To Get Credentials 🧾

### Telegram Bot Token 💬

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`.
3. Choose a bot name and username.
4. Copy the token BotFather gives you.
5. Put it in `.env` as `TELEGRAM_BOT_TOKEN`.

### Telegram Chat ID 🆔

1. Start a chat with your bot and send any message.
2. Open this URL in your browser after replacing the token:

```text
https://api.telegram.org/botYOUR_TELEGRAM_BOT_TOKEN/getUpdates
```

3. Find `"chat":{"id":...}` in the response.
4. Put that number in `.env` as `TELEGRAM_ALLOWED_CHAT_ID`.

### Google Sheet URL 📊

1. Open your Google Sheet.
2. Make sure the sheet has lead columns such as name, phone, source, notes, intent, prospect type, engagement, and fit.
3. Click `Share` and allow access for anyone with the link, or publish the sheet as CSV.
4. Copy the sheet link.
5. Put it in `.env` as `GOOGLE_SHEET_URL`.

### Zoho CRM Credentials 🏢

1. Go to the Zoho API Console.
2. Create a server-based client.
3. Copy the client ID and client secret.
4. Generate a refresh token with CRM lead read access.
5. Fill these values in `.env`:

```bash
ZOHO_CLIENT_ID=
ZOHO_CLIENT_SECRET=
ZOHO_REFRESH_TOKEN=
```

Keep the default values below unless your Zoho account uses another region:

```bash
ZOHO_ACCOUNTS_URL=https://accounts.zoho.com
ZOHO_API_BASE=https://www.zohoapis.com
```

### Vapi Credentials 📞

1. Create or open your Vapi account.
2. Create an assistant for sales calls.
3. Add or import a phone number in Vapi.
4. Copy your API key, assistant ID, and phone number ID.
5. Set the provider in `.env`:

```bash
VOICE_PROVIDER=vapi
VAPI_API_KEY=
VAPI_ASSISTANT_ID=
VAPI_PHONE_NUMBER_ID=
```

For local testing without real calls, keep:

```bash
VOICE_PROVIDER=mock
```

## Vapi Webhook Setup 📡

For live calling, your server must be available on a public HTTPS URL.

Set the webhook/server URL in Vapi to:

```text
https://YOUR_PUBLIC_DOMAIN/api/vapi/webhook?secret=YOUR_VAPI_WEBHOOK_SECRET
```

Enable these Vapi server messages:

```text
status-update
end-of-call-report
```

The app uses these events to update lead status from `calling` to `contacted` or `follow_up`.

## Running The Agent ▶️

Start the server:

```bash
python3 -m app.server
```

The server will:

- Load `.env`
- Initialize SQLite
- Sync leads
- Start the Telegram bot if a token exists
- Start the scheduler
- Serve the dashboard

## Useful URLs 🌐

```text
Dashboard:    http://127.0.0.1:8765
State API:    http://127.0.0.1:8765/api/state
Health Check: http://127.0.0.1:8765/health
```

## Telegram Controls 🎛️

After starting the bot, send `/start` in Telegram.

You can use:

- Hot leads
- Lead summary
- Call approvals
- Research tasks
- Google Sheet link
- Plain English requests like `show hot leads` or `what should I do next`

## Lead Priority Framework 🔥

The score is calculated from 0-100:

- Intent Score: 40%
- Organization Score: 25%
- Engagement Score: 20%
- Fit Score: 15%

Priority buckets:

```text
Hot:     80-100
Warm:    60-79
Nurture: 40-59
Cold:    0-39
```

## Approval And Safety 🛡️

Default mode is approval-based. The agent recommends actions, but calls require approval.

Autonomous mode is blocked unless this is set:

```bash
ALLOW_AUTONOMOUS=true
```

Use approval mode for the MVP and switch only after testing live lead flows.

## Testing ✅

Run checks before deployment:

```bash
python3 -m py_compile app/*.py tests/*.py
python3 -m unittest discover -s tests -v
```

## Production Checklist 🚢

- Rotate any token that was shared in chat or logs
- Use a public HTTPS domain
- Set environment variables on the hosting platform
- Keep `.env` out of Git
- Use `VOICE_PROVIDER=mock` until Vapi is tested
- Configure the Vapi webhook
- Add dashboard authentication before public exposure
- Back up `lead_agent.db` or move to a managed database
- Monitor logs for failed syncs, failed calls, and webhook errors

## Clone Behavior 🧬

When someone clones this repo, the server does not start automatically. They must create `.env` and run:

```bash
python3 -m app.server
```

After that, the app loads their `.env` values and starts with their own Telegram, Google Sheet, Zoho, and Vapi setup.
