from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from bot.integrations import security_tools


async def scan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /scan [type] [target]\nTypes: sast, deps, docker, secrets"
        )
        return

    scan_type = args[0].lower()
    target = " ".join(args[1:])
    target_path = security_tools.resolve_target(target)

    await update.message.reply_text(
        f"[scan] Démarrage du scan *{scan_type.upper()}* pour: `{target}`...",
        parse_mode="Markdown",
    )

    try:
        if scan_type == "sast":
            result = await security_tools.run_bandit(target_path)
            counts = result.get("counts", {})
            text = (
                f"SAST (Bandit) — Résumé:\n"
                f"🔴 Critique: {counts.get('critical', 0)}\n"
                f"🟠 High: {counts.get('high', 0)}\n"
                f"🟡 Medium: {counts.get('medium', 0)}\n"
                f"🟢 Low: {counts.get('low', 0)}\n"
            )
            # include top 5 issues as examples
            issues = result.get("issues", [])
            if issues:
                text += "\nTop findings:\n"
                for i, issue in enumerate(issues[:5], start=1):
                    filename = issue.get("filename") or "<unknown>"
                    line = issue.get("line") or issue.get("line_number") or "?"
                    test = issue.get("test_name") or ""
                    msg = issue.get("message") or issue.get("issue_text") or ""
                    text += f"{i}. {test} — {filename}:{line} — {msg}\n"

            await update.message.reply_text(text)
        elif scan_type == "deps":
            result = await security_tools.run_dependency_scan(target_path)
            counts = result.get("counts", {})
            text = (
                f"Dependency scan (pip-audit) — Résumé:\n"
                f"🔴 Critique: {counts.get('critical', 0)}\n"
                f"🟠 High: {counts.get('high', 0)}\n"
                f"🟡 Medium: {counts.get('medium', 0)}\n"
                f"🟢 Low: {counts.get('low', 0)}\n"
            )
            # include top 5 vulnerable packages
            vulns = result.get("vulns", [])
            if vulns:
                text += "\nTop vulnerable packages:\n"
                for i, v in enumerate(vulns[:5], start=1):
                    name = v.get("name")
                    version = v.get("version")
                    vlist = v.get("vulns") or []
                    first_vuln = vlist[0].get("id") if vlist and isinstance(vlist[0], dict) and vlist[0].get("id") else (vlist[0] if vlist else "")
                    text += f"{i}. {name}=={version} — {first_vuln}\n"

            await update.message.reply_text(text)
        elif scan_type == "secrets":
            result = await security_tools.run_secret_scan(target_path)
            counts = result.get("counts", {})
            text = f"Secret scan — Trouvé potential secrets: {counts.get('potential_secrets', 0)}"
            await update.message.reply_text(text)
        elif scan_type == "docker":
            # target is expected to be an image name (e.g. 'python:3.11-slim' or 'registry.example.com/repo/image:tag')
            try:
                result = await security_tools.run_trivy_scan(target)
                counts = result.get("counts", {})
                text = (
                    f"Docker image scan (Trivy) — Résumé:\n"
                    f"🔴 Critique: {counts.get('critical', 0)}\n"
                    f"🟠 High: {counts.get('high', 0)}\n"
                    f"🟡 Medium: {counts.get('medium', 0)}\n"
                    f"🟢 Low: {counts.get('low', 0)}\n"
                )
                # include top 5 trivy vulnerabilities
                vulns = result.get("vulns", [])
                if vulns:
                    text += "\nTop image vulnerabilities:\n"
                    for i, v in enumerate(vulns[:5], start=1):
                        vid = v.get("vulnerability_id") or v.get("VulnerabilityID") or ""
                        pkg = v.get("pkg") or v.get("PkgName") or ""
                        sev = v.get("severity") or v.get("Severity") or ""
                        title = v.get("title") or v.get("Title") or ""
                        text += f"{i}. [{sev}] {vid} — {pkg} — {title}\n"

                await update.message.reply_text(text)
            except Exception as exc:
                await update.message.reply_text(f"Docker image scan failed: {exc}")
        else:
            await update.message.reply_text("Type de scan inconnu. Utilisez: sast, deps, docker, secrets")
    except Exception as exc:
        await update.message.reply_text(f"Erreur lors du scan: {exc}")


async def alerts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📡 Recent Alerts:\n"
        "- No active security alerts in the last 24 hours.\n"
        "- If a vulnerability is detected, you will receive a critical notification immediately."
    )
