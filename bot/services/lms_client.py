"""
LMS API client for fetching student scores and lab submissions.

Provides all 9 backend endpoints as tools for LLM-based intent routing.
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

    # ========== Tool Methods for LLM ==========

    async def get_items(self) -> list:
        """
        Get all items (labs and tasks) from the LMS.

        Returns:
            List of items (labs and tasks)
        """
        client = await self._get_client()
        try:
            response = await client.get("/items/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}. The backend service may be down.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def get_learners(self) -> list:
        """
        Get all enrolled learners.

        Returns:
            List of learner records
        """
        client = await self._get_client()
        try:
            response = await client.get("/learners/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}. The backend service may be down.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def get_scores(self, lab: str) -> list:
        """
        Get score distribution (4 buckets) for a lab.

        Args:
            lab: Lab identifier (e.g., "lab-01")

        Returns:
            List of score distribution data
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/analytics/scores?lab={lab}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise RuntimeError(f"invalid lab identifier: {lab}. Use format like 'lab-01'.")
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def get_pass_rates(self, lab: str) -> list:
        """
        Get per-task average scores and attempt counts for a lab.

        Args:
            lab: Lab identifier (e.g., "lab-01")

        Returns:
            List of pass rate data for tasks in the lab
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/analytics/pass-rates?lab={lab}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise RuntimeError(f"invalid lab identifier: {lab}. Use format like 'lab-01'.")
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def get_timeline(self, lab: str) -> list:
        """
        Get submissions per day for a lab.

        Args:
            lab: Lab identifier (e.g., "lab-01")

        Returns:
            List of timeline data (submissions per day)
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/analytics/timeline?lab={lab}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise RuntimeError(f"invalid lab identifier: {lab}. Use format like 'lab-01'.")
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def get_groups(self, lab: str) -> list:
        """
        Get per-group scores and student counts for a lab.

        Args:
            lab: Lab identifier (e.g., "lab-01")

        Returns:
            List of group performance data
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/analytics/groups?lab={lab}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise RuntimeError(f"invalid lab identifier: {lab}. Use format like 'lab-01'.")
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def get_top_learners(self, lab: str, limit: int = 5) -> list:
        """
        Get top N learners by score for a lab.

        Args:
            lab: Lab identifier (e.g., "lab-01")
            limit: Number of top learners to return (default: 5)

        Returns:
            List of top learner records
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/analytics/top-learners?lab={lab}&limit={limit}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise RuntimeError(f"invalid parameters. Use lab='lab-01' format and limit as integer.")
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def get_completion_rate(self, lab: str) -> dict:
        """
        Get completion rate percentage for a lab.

        Args:
            lab: Lab identifier (e.g., "lab-01")

        Returns:
            Dictionary with completion rate data
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/analytics/completion-rate?lab={lab}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise RuntimeError(f"invalid lab identifier: {lab}. Use format like 'lab-01'.")
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def trigger_sync(self) -> dict:
        """
        Trigger ETL sync to refresh data from autochecker.

        Returns:
            Dictionary with sync status
        """
        client = await self._get_client()
        try:
            response = await client.post("/pipeline/sync", json={})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    # ========== Legacy Methods for Backward Compatibility ==========

    async def health_check(self) -> dict:
        """
        Check if the LMS API is healthy and get item count.

        Returns:
            Dictionary with health status and item count
        """
        try:
            items = await self.get_items()
            return {"healthy": True, "item_count": len(items)}
        except RuntimeError as e:
            raise e
