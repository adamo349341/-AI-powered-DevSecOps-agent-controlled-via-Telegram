import os
import re
from typing import Any, Dict, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from bot.integrations.gitlab import GitLabAPIError, GitLabClient


def _load_projects() -> List[str]:
    projects = os.getenv("GITLAB_PROJECTS", "").strip()
    return [project.strip() for project in projects.split(",") if project.strip()]


def _get_env_value(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"Environment variable {key} is required")
    return value


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gitlab_token = _get_env_value("GITLAB_TOKEN")
    base_url = os.getenv("GITLAB_BASE_URL", "https://gitlab.com/api/v4")
    projects = _load_projects()

    if not projects:
        await update.message.reply_text(
            "No projects configured. Set GITLAB_PROJECTS in your environment as a comma-separated list."
        )
        return

    summary_lines: List[str] = ["📊 *Pipeline Status Overview*\n"]
    async with GitLabClient(gitlab_token, base_url) as client:
        for project in projects:
            try:
                pipelines = await client.list_project_pipelines(project, per_page=3)
                if not pipelines:
                    summary_lines.append(f"*{project}* — No recent pipelines found.")
                    continue
                latest = pipelines[0]
                status = latest.get("status", "unknown").capitalize()
                ref = latest.get("ref", "unknown")
                iid = latest.get("id") or latest.get("iid")
                summary_lines.append(
                    f"*{project}* — `{ref}` — {status} — pipeline `{iid}`"
                )
            except GitLabAPIError as exc:
                summary_lines.append(f"*{project}* — ⚠️ Error: {exc}")

    await update.message.reply_markdown_v2("\n".join(summary_lines))


async def run_pipeline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gitlab_token = _get_env_value("GITLAB_TOKEN")
    base_url = os.getenv("GITLAB_BASE_URL", "https://gitlab.com/api/v4")
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /run_pipeline [project] [branch]\nExample: /run_pipeline group/project main"
        )
        return

    project = args[0]
    branch = args[1]
    variables = {arg.split("=")[0]: arg.split("=")[1] for arg in args[2:] if "=" in arg}

    async with GitLabClient(gitlab_token, base_url) as client:
        try:
            pipeline = await client.trigger_pipeline(project, branch, variables)
            pipeline_id = pipeline.get("id") or pipeline.get("iid")
            await update.message.reply_text(
                f"🚀 Pipeline triggered for *{project}* on branch *{branch}*\n"
                f"Pipeline ID: `{pipeline_id}`",
                parse_mode="Markdown",
            )
        except GitLabAPIError as exc:
            await update.message.reply_text(
                f"Failed to trigger pipeline for *{project}* on branch *{branch}*:\n{exc}",
                parse_mode="Markdown",
            )


async def stop_pipeline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gitlab_token = _get_env_value("GITLAB_TOKEN")
    base_url = os.getenv("GITLAB_BASE_URL", "https://gitlab.com/api/v4")
    args = context.args

    if len(args) < 1:
        await update.message.reply_text("Usage: /stop_pipeline [pipeline_id]")
        return

    pipeline_id = None
    try:
        pipeline_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Pipeline ID must be an integer.")
        return

    projects = _load_projects()
    if not projects:
        await update.message.reply_text(
            "No projects configured. Cannot search for pipeline to stop."
        )
        return

    async with GitLabClient(gitlab_token, base_url) as client:
        for project in projects:
            try:
                await client.cancel_pipeline(project, pipeline_id)
                await update.message.reply_text(
                    f"🛑 Pipeline `{pipeline_id}` canceled for project *{project}*.",
                    parse_mode="Markdown",
                )
                return
            except GitLabAPIError:
                continue

    await update.message.reply_text(
        f"Could not cancel pipeline `{pipeline_id}`. Ensure the pipeline ID is correct and the project is monitored.",
        parse_mode="Markdown",
    )


async def logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gitlab_token = _get_env_value("GITLAB_TOKEN")
    base_url = os.getenv("GITLAB_BASE_URL", "https://gitlab.com/api/v4")
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /logs [pipeline_id] [job_name]\nExample: /logs 12345 test"
        )
        return

    pipeline_id_str, job_name = args[0], " ".join(args[1:])
    if not re.match(r"^\d+$", pipeline_id_str):
        await update.message.reply_text("Pipeline ID must be a number.")
        return

    pipeline_id = int(pipeline_id_str)
    projects = _load_projects()

    if not projects:
        await update.message.reply_text(
            "No projects configured. Cannot fetch logs without GITLAB_PROJECTS."
        )
        return

    async with GitLabClient(gitlab_token, base_url) as client:
        for project in projects:
            try:
                jobs = await client.get_pipeline_jobs(project, pipeline_id)
                for job in jobs:
                    if job_name.lower() in job.get("name", "").lower():
                        trace = await client.get_job_trace(project, job["id"])
                        text = trace or "No log output available."
                        if len(text) > 3900:
                            text = text[-3900:]
                        await update.message.reply_text(
                            f"📄 Logs for job *{job['name']}* in pipeline `{pipeline_id}`:\n\n{text}",
                            parse_mode="Markdown",
                        )
                        return
            except GitLabAPIError:
                continue

    await update.message.reply_text(
        f"Could not locate logs for pipeline `{pipeline_id}` and job *{job_name}*."
    )
