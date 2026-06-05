import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from bot.handlers import deploy, general, pipeline, security

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN must be set in environment or .env file")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=LOG_LEVEL,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Update caused exception: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Sorry, something went wrong. Please try again or contact the admin."
        )


def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # General command handlers
    application.add_handler(CommandHandler("start", general.start_handler))
    application.add_handler(CommandHandler("help", general.help_handler))

    # Pipeline command handlers
    application.add_handler(CommandHandler("status", pipeline.status_handler))
    application.add_handler(CommandHandler("run_pipeline", pipeline.run_pipeline_handler))
    application.add_handler(CommandHandler("stop_pipeline", pipeline.stop_pipeline_handler))
    application.add_handler(CommandHandler("logs", pipeline.logs_handler))

    # Security handlers
    application.add_handler(CommandHandler("scan", security.scan_handler))
    application.add_handler(CommandHandler("alerts", security.alerts_handler))

    # Deploy flow uses a conversation handler for confirmation
    deploy_flow = ConversationHandler(
        entry_points=[CommandHandler("deploy", deploy.deploy_handler)],
        states={
            deploy.CONFIRM_DEPLOY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, deploy.confirmation_response)
            ]
        },
        fallbacks=[CommandHandler("cancel", deploy.cancel_handler)],
        name="deploy_conversation",
        persistent=False,
    )
    application.add_handler(deploy_flow)

    application.add_error_handler(error_handler)

    logger.info("Starting DevSecOps Telegram agent")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
