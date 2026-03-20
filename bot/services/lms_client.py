"""
LMS API client for fetching student scores and lab submissions.
"""

import os
from typing import Optional

import httpx


class LmsClient:
    """Client for the LMS API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the LMS client.

        Args:
            base_url: LMS API base URL (default: from LMS_API_URL env)
            api_key: LMS API key (default: from LMS_API_KEY env)
        """
        self.base_url = base_url or os.getenv("LMS_API_URL", "http://localhost:42002")
        self.api_key = api_key or os.getenv("LMS_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_student_scores(self, telegram_id: int) -> dict:
        """
        Fetch scores for a student by Telegram ID.

        Args:
            telegram_id: The student's Telegram user ID

        Returns:
            Dictionary with score data
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/api/scores/{telegram_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": str(e), "scores": []}

    async def get_lab_submissions(self, telegram_id: int) -> list:
        """
        Fetch lab submissions for a student by Telegram ID.

        Args:
            telegram_id: The student's Telegram user ID

        Returns:
            List of lab submission data
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/api/labs/{telegram_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return []

    async def health_check(self) -> bool:
        """
        Check if the LMS API is healthy.

        Returns:
            True if healthy, False otherwise
        """
        client = await self._get_client()
        try:
            response = await client.get("/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
