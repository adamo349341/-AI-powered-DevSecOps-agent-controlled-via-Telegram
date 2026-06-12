from telegram import Update
from telegram.ext import ContextTypes


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome to the AI-powered DevSecOps agent!\n\n"
        "I can control your GitLab CI/CD pipelines, run security scans, deploy applications, and deliver alerts directly in Telegram.\n\n"
        "Use /help to see available commands."
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Show the welcome message\n"
        "/help - List commands\n"
        "/status - Current pipeline status for configured projects\n"
        "/run_pipeline [project] [branch] - Trigger a GitLab pipeline\n"
        "/stop_pipeline [pipeline_id] - Cancel a running pipeline\n"
        "/logs [pipeline_id] [job_name] - Fetch job logs\n"
        "/scan [type] [target] - Run a security scan (sast, deps, docker, secrets)\n"
        "/deploy [env] [version] - Deploy a release with confirmation\n"
        "/alerts - Show recent security alerts\n"
    )


async def myid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the numeric chat id for the user or group. Useful for populating BOT_ADMIN_IDS."""
    chat = update.effective_chat
    if chat:
        await update.message.reply_text(f"Your chat id is: {chat.id}")
    else:
        await update.message.reply_text("Could not determine chat id.")
