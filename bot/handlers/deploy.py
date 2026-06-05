from typing import Any

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

CONFIRM_DEPLOY = 1


def _build_deploy_message(env: str, version: str) -> str:
    return (
        f"⚙️ Ready to deploy version *{version}* to *{env.upper()}* environment.\n\n"
        "Please confirm by replying with `yes` or cancel with `/cancel`."
    )


async def deploy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /deploy [env] [version]\nExample: /deploy staging 1.2.0"
        )
        return CONFIRM_DEPLOY

    env = args[0].lower()
    version = args[1]
    if env not in {"dev", "staging", "prod"}:
        await update.message.reply_text(
            "Environment must be one of: dev, staging, prod."
        )
        return CONFIRM_DEPLOY

    context.user_data["deploy_action"] = {"env": env, "version": version}
    await update.message.reply_text(
        _build_deploy_message(env, version), parse_mode="Markdown"
    )
    return CONFIRM_DEPLOY


async def confirmation_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    action = context.user_data.get("deploy_action")

    if not action:
        await update.message.reply_text(
            "No pending deployment found. Use /deploy [env] [version] to start a new deployment."
        )
        return ConversationHandler.END

    if text in {"yes", "y", "confirm", "deploy"}:
        env = action["env"]
        version = action["version"]
        if env == "prod":
            await update.message.reply_text(
                "⚠️ Production deploy confirmed. Executing deployment now..."
            )
        else:
            await update.message.reply_text(
                f"🚀 Deploying version *{version}* to *{env}*...",
                parse_mode="Markdown",
            )
        # Placeholder for deploy orchestration.
        await update.message.reply_text(
            f"✅ Deployment started for *{version}* to *{env}*. You will be notified when complete.",
            parse_mode="Markdown",
        )
        context.user_data.pop("deploy_action", None)
        return ConversationHandler.END

    if text in {"no", "n", "cancel"}:
        await update.message.reply_text("Deployment cancelled.")
        context.user_data.pop("deploy_action", None)
        return ConversationHandler.END

    await update.message.reply_text(
        "Please reply with `yes` to confirm or `/cancel` to abort.",
        parse_mode="Markdown",
    )
    return CONFIRM_DEPLOY


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("deploy_action", None)
    await update.message.reply_text("Deployment flow cancelled.")
    return ConversationHandler.END
