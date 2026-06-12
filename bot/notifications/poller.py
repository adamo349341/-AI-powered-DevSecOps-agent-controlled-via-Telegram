import asyncio
import logging
import os
from typing import Dict, Optional

from bot.integrations.gitlab import GitLabClient, GitLabAPIError

logger = logging.getLogger(__name__)


class PipelinePoller:
    def __init__(self, token: str, projects: Optional[list] = None, interval: int = 15, bot=None, admin_ids: Optional[list] = None):
        self.token = token
        self.base_url = os.getenv("GITLAB_BASE_URL", "https://gitlab.com/api/v4")
        self.interval = interval
        self.projects = projects or []
        self._running = False
        self._seen: Dict[int, str] = {}  # pipeline_id -> status
        self.bot = bot
        self.admin_ids = admin_ids or []

    async def _check_once(self):
        async with GitLabClient(self.token, self.base_url) as client:
            for proj in self.projects:
                try:
                    pipelines = await client.list_project_pipelines(proj, per_page=5)
                except GitLabAPIError as exc:
                    logger.warning("Failed to list pipelines for %s: %s", proj, exc)
                    continue
                for p in pipelines:
                    pid = p.get("id") or p.get("iid")
                    status = p.get("status")
                    if pid is None:
                        continue
                    prev = self._seen.get(pid)
                    if prev is None:
                        self._seen[pid] = status
                    elif prev != status:
                        # status changed
                        self._seen[pid] = status
                        msg = f"Pipeline {pid} (project {proj}) status changed: {prev} -> {status}"
                        logger.info(msg)
                        # send telegram notifications to admin ids if bot configured
                        if self.bot and self.admin_ids:
                            for chat_id in self.admin_ids:
                                try:
                                    # Fire-and-forget send with retries
                                    asyncio.create_task(self._send_message_with_retries(chat_id, msg))
                                except Exception:
                                    logger.exception("Failed to schedule pipeline notification to %s", chat_id)

    async def _send_message_with_retries(self, chat_id: int, text: str, tries: int = 3):
        """Send a message to Telegram with simple retries and exponential backoff."""
        delay = 1.0
        for attempt in range(1, tries + 1):
            try:
                await self.bot.send_message(chat_id=chat_id, text=text)
                return True
            except Exception as exc:
                logger.warning("Attempt %d: failed to send message to %s: %s", attempt, chat_id, exc)
                if attempt == tries:
                    logger.exception("All retries failed sending message to %s", chat_id)
                    return False
                await asyncio.sleep(delay)
                delay *= 2

            async def check_once(self):
                """Public wrapper to perform a single poll/check. Useful when running via a job queue."""
                await self._check_once()

    async def run(self):
        self._running = True
        while self._running:
            try:
                await self._check_once()
            except Exception:
                logger.exception("Error during pipeline poll")
            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False
