"""
LLM API client for natural language responses.
"""

import os
from typing import Optional

import httpx


class LlmClient:
    """Client for the LLM API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the LLM client.

        Args:
            base_url: LLM API base URL (default: from LLM_API_BASE_URL env)
            api_key: LLM API key (default: from LLM_API_KEY env)
            model: Model name to use (default: from LLM_API_MODEL env)
        """
        self.base_url = base_url or os.getenv("LLM_API_BASE_URL", "http://localhost:42005/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_API_MODEL", "coder-model")
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

    async def chat(self, user_message: str, context: Optional[str] = None) -> str:
        """
        Send a message to the LLM and get a response.

        Args:
            user_message: The user's message
            context: Optional context to include in the prompt

        Returns:
            LLM response text
        """
        client = await self._get_client()
        
        system_prompt = "You are a helpful assistant for SE Toolkit Lab 7."
        if context:
            system_prompt += f"\n\nContext: {context}"

        try:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
        except httpx.HTTPError as e:
            return f"LLM API error: {e}"

    async def health_check(self) -> bool:
        """
        Check if the LLM API is healthy.

        Returns:
            True if healthy, False otherwise
        """
        client = await self._get_client()
        try:
            response = await client.get("/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
