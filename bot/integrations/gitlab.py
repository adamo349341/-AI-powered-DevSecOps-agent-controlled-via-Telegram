import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


class GitLabAPIError(Exception):
    pass


class GitLabClient:
    def __init__(self, token: str, base_url: str = "https://gitlab.com/api/v4"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        if not self.base_url.endswith("/api/v4"):
            self.base_url = f"{self.base_url}/api/v4"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "GitLabClient":
        headers = {
            "Private-Token": self.token,
            "Content-Type": "application/json",
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.session is not None and not self.session.closed:
            await self.session.close()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        text_response: bool = False,
    ) -> Any:
        if self.session is None:
            raise RuntimeError("GitLabClient session has not been initialized")

        url = f"{self.base_url}/{path.lstrip('/') }"
        logger.debug("GitLab request %s %s %s", method, url, params)
        async with self.session.request(method, url, params=params, json=json) as response:
            text = await response.text()
            if response.status >= 400:
                logger.error("GitLab API error %s %s: %s", response.status, url, text)
                raise GitLabAPIError(
                    f"GitLab API request failed ({response.status}): {text}"
                )
            if text_response:
                return text
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return await response.json()
            try:
                return await response.json()
            except aiohttp.ContentTypeError:
                return text

    @staticmethod
    def _project_path_encoded(project_path: str) -> str:
        return urllib.parse.quote_plus(project_path)

    async def resolve_project_id(self, project_identifier: Union[int, str]) -> int:
        if isinstance(project_identifier, int):
            return project_identifier
        encoded_path = self._project_path_encoded(project_identifier)
        project = await self._request("GET", f"projects/{encoded_path}")
        return int(project["id"])

    async def trigger_pipeline(
        self,
        project: Union[int, str],
        ref: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        project_id = await self.resolve_project_id(project)
        payload = {"ref": ref}
        if variables:
            payload["variables"] = [{"key": key, "value": value} for key, value in variables.items()]
        return await self._request("POST", f"projects/{project_id}/pipeline", json=payload)

    async def cancel_pipeline(
        self,
        project: Union[int, str],
        pipeline_id: int,
    ) -> Dict[str, Any]:
        project_id = await self.resolve_project_id(project)
        return await self._request("POST", f"projects/{project_id}/pipelines/{pipeline_id}/cancel")

    async def get_pipeline(self, project: Union[int, str], pipeline_id: int) -> Dict[str, Any]:
        project_id = await self.resolve_project_id(project)
        return await self._request("GET", f"projects/{project_id}/pipelines/{pipeline_id}")

    async def list_project_pipelines(
        self,
        project: Union[int, str],
        ref: Optional[str] = None,
        per_page: int = 5,
    ) -> List[Dict[str, Any]]:
        project_id = await self.resolve_project_id(project)
        params: Dict[str, Any] = {"per_page": per_page}
        if ref:
            params["ref"] = ref
        return await self._request("GET", f"projects/{project_id}/pipelines", params=params)

    async def get_pipeline_jobs(
        self,
        project: Union[int, str],
        pipeline_id: int,
    ) -> List[Dict[str, Any]]:
        project_id = await self.resolve_project_id(project)
        return await self._request("GET", f"projects/{project_id}/pipelines/{pipeline_id}/jobs")

    async def get_job_trace(
        self,
        project: Union[int, str],
        job_id: int,
    ) -> str:
        project_id = await self.resolve_project_id(project)
        return await self._request("GET", f"projects/{project_id}/jobs/{job_id}/trace", text_response=True)

    async def search_projects(self, query: str, per_page: int = 20) -> List[Dict[str, Any]]:
        params = {"search": query, "per_page": per_page}
        return await self._request("GET", "projects", params=params)
