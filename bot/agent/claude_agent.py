import os
from typing import Any, Dict, Optional

import aiohttp


class ClaudeAgent:
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

    async def analyze_intent(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set to use the AI agent")

        url = "https://api.anthropic.com/v1/complete"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens_to_sample": 300,
            "temperature": 0.2,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
