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

    async def get_items(self) -> list:
        """
        Fetch all items (labs and tasks) from the LMS.

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

    async def get_pass_rates(self, lab: str) -> list:
        """
        Fetch pass rates for a specific lab.

        Args:
            lab: The lab identifier (e.g., "lab-04")

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
                raise RuntimeError(f"invalid lab identifier: {lab}. Use format like 'lab-04'.")
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}. The backend service may be down.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")

    async def health_check(self) -> dict:
        """
        Check if the LMS API is healthy and get item count.

        Returns:
            Dictionary with health status and item count
        """
        client = await self._get_client()
        try:
            response = await client.get("/items/")
            response.raise_for_status()
            items = response.json()
            return {"healthy": True, "item_count": len(items)}
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP {e.response.status_code} {e.response.reason_phrase}. The backend service may be down.")
        except httpx.ConnectError as e:
            raise RuntimeError(f"connection refused ({self.base_url}). Check that the services are running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"{str(e)}. Check that the backend is running.")
