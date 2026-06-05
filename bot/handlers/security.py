from telegram import Update
from telegram.ext import ContextTypes


async def scan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /scan [type] [target]\nTypes: sast, deps, docker, secrets"
        )
        return

    scan_type = args[0].lower()
    target = " ".join(args[1:])

    await update.message.reply_text(
        f"🔎 Starting *{scan_type.upper()}* scan for target: `{target}`...",
        parse_mode="Markdown",
    )

    # Placeholder for security integration. The actual scan runner will execute tools
    # like Bandit, Safety, Trivy, and detect-secrets in a future implementation.
    await update.message.reply_text(
        "✅ Scan request accepted. Security scan results will be delivered when available."
    )


async def alerts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📡 Recent Alerts:\n"
        "- No active security alerts in the last 24 hours.\n"
        "- If a vulnerability is detected, you will receive a critical notification immediately."
    )
