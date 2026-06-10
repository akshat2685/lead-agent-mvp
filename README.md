# Edysor AI Revenue Intelligence OS (v3)

Welcome to the **Edysor AI Lead Agent MVP v3**. This project has evolved from a simple SQLite-backed Telegram routing bot into a production-grade, AI-orchestrated Revenue Intelligence Operating System.

## Version 3 Upgrades
This version introduces 10 massive architectural upgrades:
1. **Security & Authentication**: JWT + bcrypt role-based access control (Admin, Agent, Viewer) and a Web UI.
2. **Database Upgrade**: Scalable `SQLAlchemy` ORM supporting `PostgreSQL` connection pooling, managed by `Alembic`.
3. **AI-Powered Lead Scoring**: Dynamic LLM-driven scoring with 24-hour result caching.
4. **Multi-Channel Outreach**: Intelligent `ChannelRouter` directing Hot leads to Voice (Scida), Warm leads to WhatsApp, and Nurture leads to Email.
5. **Autonomous Mode & Guardrails**: Daily spend caps, business hour enforcement, and an emergency `/stop` switch.
6. **Lead Enrichment**: Auto-research pipelines for Email Validation and LinkedIn Scraping prior to scoring.
7. **Analytics Dashboard**: Chart.js visualizations for Conversion Funnels, Agent Productivity, and Revenue Attribution.
8. **Docker & CI/CD**: Fully containerized stack (`app`, `db`, `redis`) with GitHub Actions deployment workflows.
9. **Bi-Directional CRM Sync**: Automatically push transcripts, LLM scores, and bucket categorizations straight into Zoho CRM.
10. **Conversation Memory**: LLM-generated summaries of past interactions are seamlessly injected into outbound AI outreach prompts.

## Prerequisites & Getting Started

Before you can completely run this in production, you **MUST** configure the external APIs:

1. **Environment Setup:**
   Duplicate `.env.example` and rename it to `.env`.
   
2. **Required API Keys:**
   - `OPENAI_API_KEY`: Required for the Lead Scorer, Orchestrator, and Memory engine.
   - `TELEGRAM_BOT_TOKEN`: Required to boot the bot.
   - `SCIDA_VOICE_AGENT_KEY` / `SCIDA_CHAT_AGENT_KEY`: The API keys for Scida voice/chat agents.
   - `PROXYCURL_API_KEY` & `ZEROBOUNCE_API_KEY` (Optional): If you want live Lead Enrichment to work.
   - `ZOHO_*` (Optional): If you want the Bi-Directional CRM sync to activate.

3. **Connecting the "Mock" APIs:**
   The architecture is built, but the final network requests to 3rd party providers are currently stubbed. 
   - Open `app/channels/voice.py`, `whatsapp.py`, `email.py`, and `sms.py`.
   - Add Python `requests.post()` logic using the specific schema of your provider (Twilio, SendGrid, Scida).
   - Open `app/zoho_sync.py` and uncomment the `requests.post()` calls.

## Running the Application

### Option A: Docker (Recommended)
This boots the Web App, PostgreSQL 15, and Redis caching.
```bash
docker-compose up --build -d
```
Visit `http://localhost:8765/login` to see your new dashboard! The default admin login is `admin@edysor.ai` / `admin123`.

### Option B: Local Python Environment
If you don't use Docker, you can run it via Python with SQLite fallback:
```bash
pip install -r requirements.txt
alembic init migrations
python -m app.server
```
*In a separate terminal, start the bot:*
```bash
python -m app.bot.telegram_handlers
```
