"""CareerOS REST API HTTP client (aiohttp-style via httpx async)."""

from typing import Optional
import httpx

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("careeros.api_client")


class CareerOSApiClient:
    """Thin async HTTP client for CareerOS backend REST API."""

    def __init__(self, base_url: Optional[str] = None, api_token: Optional[str] = None):
        self._base_url = (base_url or settings.careeros_api_url).rstrip("/")
        self._token = api_token or settings.careeros_api_token

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def upload_resume(self, pdf_bytes: bytes, filename: str = "resume.pdf") -> str:
        """Upload a PDF resume to CareerOS and return the resumeId."""
        url = f"{self._base_url}/api/v1/resume/upload"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = client.build_request(
                "POST",
                url,
                headers={k: v for k, v in self._headers().items() if k != "Content-Type"},
                files={"file": (filename, pdf_bytes, "application/pdf")},
            )
            resp = await client.send(response)
            resp.raise_for_status()
            data = resp.json()
            resume_id = data.get("resumeId") or data.get("id")
            if not resume_id:
                raise ValueError(f"CareerOS resume upload returned no resumeId: {data}")
            logger.info("Resume uploaded, resumeId=%s", resume_id)
            return str(resume_id)

    async def trigger_github_sync(self, user_id: int, github_username: str) -> str:
        """Trigger GitHub repository sync for a user and return the syncId."""
        url = f"{self._base_url}/api/v1/github/sync"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers=self._headers(),
                json={"userId": user_id, "githubUsername": github_username},
            )
            resp.raise_for_status()
            data = resp.json()
            sync_id = data.get("syncId") or data.get("id")
            logger.info("GitHub sync triggered for user=%s, syncId=%s", user_id, sync_id)
            return str(sync_id) if sync_id else ""

    async def get_candidate_graph(self, user_id: int) -> dict:
        """Return the CandidateGraph status dict for the given user."""
        url = f"{self._base_url}/api/v1/candidate/{user_id}/graph"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def trigger_digest(self, user_id: Optional[int] = None) -> dict:
        """Manually trigger a job digest run. Returns the trigger result."""
        url = f"{self._base_url}/api/v1/digest/trigger"
        payload: dict = {}
        if user_id is not None:
            payload["userId"] = user_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    async def get_digest_status(self) -> dict:
        """Return the last digest run metadata from CareerOS."""
        url = f"{self._base_url}/api/v1/digest/status"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()


careeros_client = CareerOSApiClient()
