import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from app.agent import (
    agent_orchestrator,
    approve_lead,
    lead_handler,
    process_approved_lead,
    reject_lead,
    scoring_engine,
    scoring_service,
)
from app.db import get_dedup_report, get_lead_history, init_database, list_pending_review, query_lead

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Lead agent scaffold ready. External integrations are intentionally blank.",
    )


def help_command(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "Commands:\n"
            "/dedup_report - duplicate tracking stats\n"
            "/lead_history <id> - audit trail for a lead\n"
            "/approve <id> - approve and route a lead\n"
            "/reject <id> [reason] - reject a lead\n"
            "/route <id> - route a lead by score\n"
            "/review_queue - leads waiting for review\n"
        ),
    )


def echo(update, context):
    lead_data = lead_handler(update.message.text)
    lead_data = scoring_service(lead_data)
    lead_data = agent_orchestrator(lead_data)
    response = scoring_engine(lead_data)
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)


def dedup_report(update, context):
    stats, by_source = get_dedup_report()
    msg = (
        "Lead Deduplication Report\n\n"
        f"Total leads: {stats['total_leads'] or 0}\n"
        f"Duplicates caught: {stats['duplicates_found'] or 0}\n"
        f"Unique sources: {stats['sources_count'] or 0}\n\n"
        "By source:\n"
    )
    for row in by_source:
        msg += f"- {row['source']}: {row['count']}\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


def lead_history_command(update, context):
    if not context.args:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /lead_history <lead_id>")
        return
    try:
        lead_id = int(context.args[0])
    except ValueError:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Lead id must be a number.")
        return

    lead = query_lead(lead_id)
    if not lead:
        context.bot.send_message(chat_id=update.effective_chat.id, text="No lead found for that id.")
        return

    rows = get_lead_history(lead_id)
    msg = f"Lead {lead_id} History\n\n"
    for row in rows:
        msg += f"{row['timestamp']} | {row['action']} | {row['changed_by']}\n"
        if row["notes"]:
            msg += f"{row['notes']}\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


def approve_command(update, context):
    if not context.args:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /approve <lead_id>")
        return
    try:
        lead_id = int(context.args[0])
    except ValueError:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Lead id must be a number.")
        return

    approved_by = update.effective_user.username or update.effective_user.full_name or "telegram"
    approve_lead(lead_id, approved_by)
    result = process_approved_lead(lead_id)
    if result.get("error"):
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Approved, but routing failed: {result['error']}")
        return
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Lead {lead_id} approved and queued for {result['channel']}.",
    )


def reject_command(update, context):
    if not context.args:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /reject <lead_id> [reason]")
        return
    try:
        lead_id = int(context.args[0])
    except ValueError:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Lead id must be a number.")
        return

    reason = " ".join(context.args[1:]).strip()
    rejected_by = update.effective_user.username or update.effective_user.full_name or "telegram"
    reject_lead(lead_id, rejected_by, reason)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Lead {lead_id} rejected.")


def route_command(update, context):
    if not context.args:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /route <lead_id>")
        return
    try:
        lead_id = int(context.args[0])
    except ValueError:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Lead id must be a number.")
        return

    result = process_approved_lead(lead_id)
    if result.get("error"):
        context.bot.send_message(chat_id=update.effective_chat.id, text=result["error"])
        return
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Lead {lead_id} routed to {result['channel']}.")


def review_queue(update, context):
    leads = list_pending_review()
    if not leads:
        context.bot.send_message(chat_id=update.effective_chat.id, text="No leads are awaiting review.")
        return
    msg = "Pending Review Leads\n\n"
    for lead in leads[:10]:
        msg += f"{lead['id']} | {lead.get('name') or 'Unknown'} | score={lead.get('score') or 0} | status={lead.get('status')}\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


def main():
    init_database()
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("dedup_report", dedup_report))
    dispatcher.add_handler(CommandHandler("lead_history", lead_history_command))
    dispatcher.add_handler(CommandHandler("approve", approve_command))
    dispatcher.add_handler(CommandHandler("reject", reject_command))
    dispatcher.add_handler(CommandHandler("route", route_command))
    dispatcher.add_handler(CommandHandler("review_queue", review_queue))
    dispatcher.add_handler(MessageHandler(Filters.text, echo))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
