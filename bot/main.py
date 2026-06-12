import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from bot.handlers import deploy, general, pipeline, security
from bot.notifications.poller import PipelinePoller

from telegram.ext import Application

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
    application: Application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # General command handlers
    application.add_handler(CommandHandler("start", general.start_handler))
    application.add_handler(CommandHandler("help", general.help_handler))
    application.add_handler(CommandHandler("myid", general.myid_handler))

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

    # Start a background poller to watch pipelines and notify admins
    gitlab_token = os.getenv("GITLAB_TOKEN")
    projects = [p.strip() for p in os.getenv("GITLAB_PROJECTS", "").split(",") if p.strip()]
    admin_ids = [int(i) for i in os.getenv("BOT_ADMIN_IDS", "").split(",") if i.strip()]

    poller = None
    poller_thread = None

    async def _start_and_poll():
        nonlocal poller
        if gitlab_token and projects:
            poller = PipelinePoller(gitlab_token, projects=projects, interval=20, bot=application.bot, admin_ids=admin_ids)
            await poller.run()

    # schedule the poller in the application as a background task
    logger.info("Scheduling pipeline poller task (if configured)")
    if gitlab_token and projects:
        # prefer JobQueue if available (user can install python-telegram-bot[job-queue])
        jqueue = getattr(application, "job_queue", None)
        if jqueue is not None:
            try:
                # schedule poller.check_once via job queue repeating job
                logger.info("Using Application.job_queue to schedule poller.check_once every 20s")
                # create a job that calls poller.check_once; we need a small wrapper
                async def _job_wrapper(ctx: ContextTypes.DEFAULT_TYPE):
                    nonlocal poller
                    if poller is None:
                        poller = PipelinePoller(gitlab_token, projects=projects, interval=20, bot=application.bot, admin_ids=admin_ids)
                    try:
                        await poller.check_once()
                    except Exception:
                        logger.exception("Error running scheduled poller job")

                # run every `interval` seconds
                jqueue.run_repeating(_job_wrapper, interval=20)
            except Exception:
                logger.exception("Failed to schedule poller with JobQueue; falling back to background task")
                try:
                    import asyncio as _asyncio

                    _asyncio.create_task(_start_and_poll())
                except Exception:
                    # last-resort: use loop.create_task
                    import asyncio as _asyncio

                    _asyncio.get_event_loop().create_task(_start_and_poll())
        else:
            # fallback: start full poll loop in a dedicated background thread
            try:
                import threading

                def _runner():
                    import asyncio

                    nonlocal poller
                    if gitlab_token and projects:
                        poller = PipelinePoller(gitlab_token, projects=projects, interval=20, bot=application.bot, admin_ids=admin_ids)
                        asyncio.run(poller.run())

                poller_thread = threading.Thread(target=_runner, name="PipelinePollerThread", daemon=True)
                poller_thread.start()
            except Exception:
                logger.exception("Failed to start poller thread")

    logger.info("Starting DevSecOps Telegram agent")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Stop poller when application stops
        if poller:
            poller.stop()


if __name__ == "__main__":
    main()
