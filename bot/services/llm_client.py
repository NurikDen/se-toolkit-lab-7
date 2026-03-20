"""
LLM API client for natural language responses with tool calling support.

Supports OpenAI-compatible tool calling API for LLM-based intent routing.
"""

import json
import os
import sys
from typing import Any, Optional

import httpx


class LlmClient:
    """Client for the LLM API with tool calling support."""

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

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: str = "auto",
    ) -> dict:
        """
        Send messages to the LLM and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions for function calling
            tool_choice: How to use tools ("auto", "required", or "none")

        Returns:
            Dict with 'content' (text response) and/or 'tool_calls' (list of tool calls)
        """
        client = await self._get_client()

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            result = {
                "content": message.get("content", ""),
            }

            if "tool_calls" in message and message["tool_calls"]:
                result["tool_calls"] = message["tool_calls"]

            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise RuntimeError("LLM API authentication failed (401). Token may have expired.")
            raise RuntimeError(f"LLM API error: HTTP {e.response.status_code} {e.response.reason_phrase}")
        except httpx.ConnectError as e:
            raise RuntimeError(f"LLM connection refused ({self.base_url}). Check that the LLM service is running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"LLM API error: {str(e)}")

    async def chat_with_tools(
        self,
        user_message: str,
        tools: list[dict],
        system_prompt: Optional[str] = None,
        max_iterations: int = 5,
        debug: bool = False,
    ) -> str:
        """
        Chat with the LLM using tool calling loop.

        The LLM can call tools, we execute them, feed results back,
        and continue until the LLM has enough information to answer.

        Args:
            user_message: The user's message
            tools: List of tool definitions (function schemas)
            system_prompt: Optional system prompt
            max_iterations: Maximum tool call iterations to prevent loops
            debug: Whether to print debug info to stderr

        Returns:
            Final LLM response text
        """
        # Build initial messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_message})

        # Tool call loop
        for iteration in range(max_iterations):
            if debug:
                print(f"[loop] Iteration {iteration + 1}/{max_iterations}", file=sys.stderr)

            # Call LLM
            result = await self.chat(messages, tools=tools, tool_choice="auto")

            # Check if LLM returned tool calls
            tool_calls = result.get("tool_calls", [])

            if not tool_calls:
                # No tool calls - LLM has final answer
                return result.get("content", "I don't have enough information to answer that.")

            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                func_name = function.get("name", "")
                func_args_str = function.get("arguments", "{}")

                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    func_args = {}

                if debug:
                    print(f"[tool] LLM called: {func_name}({func_args})", file=sys.stderr)

                # Execute the tool
                try:
                    tool_result = await self._execute_tool(func_name, func_args)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": json.dumps(tool_result, default=str),
                    })
                    if debug:
                        result_preview = str(tool_result)[:100]
                        print(f"[tool] Result: {result_preview}...", file=sys.stderr)
                except Exception as e:
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": f"Error executing {func_name}: {str(e)}",
                    })
                    if debug:
                        print(f"[tool] Error: {e}", file=sys.stderr)

            # Feed tool results back to LLM
            messages.append({"role": "assistant", "content": result.get("content", ""), "tool_calls": tool_calls})
            messages.extend(tool_results)

            if debug:
                print(f"[summary] Feeding {len(tool_results)} tool result(s) back to LLM", file=sys.stderr)

        # If we get here, we hit max iterations
        return "I'm having trouble gathering all the information needed. Please try rephrasing your question."

    async def _execute_tool(self, name: str, arguments: dict) -> Any:
        """
        Execute a tool by name with the given arguments.

        Args:
            name: Tool name (must match a method on LmsClient)
            arguments: Tool arguments as dict

        Returns:
            Tool execution result
        """
        from services.lms_client import LmsClient

        client = LmsClient()
        try:
            # Get the method by name
            method = getattr(client, name, None)
            if not method:
                raise ValueError(f"Unknown tool: {name}")

            # Call the method with arguments
            if arguments:
                result = await method(**arguments)
            else:
                result = await method()

            return result
        finally:
            await client.close()

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


# ========== Tool Definitions ==========

def get_tool_definitions() -> list[dict]:
    """
    Get OpenAI-compatible tool definitions for all LMS endpoints.

    Returns:
        List of tool definitions for LLM function calling
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_items",
                "description": "Get list of all labs and tasks available in the system",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_learners",
                "description": "Get list of all enrolled learners/students",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_scores",
                "description": "Get score distribution (4 buckets) for a specific lab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier in format 'lab-01', 'lab-02', etc.",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pass_rates",
                "description": "Get per-task average scores and attempt counts for a specific lab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier in format 'lab-01', 'lab-02', etc.",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_timeline",
                "description": "Get submission timeline (submissions per day) for a specific lab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier in format 'lab-01', 'lab-02', etc.",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_groups",
                "description": "Get per-group performance scores and student counts for a specific lab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier in format 'lab-01', 'lab-02', etc.",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_top_learners",
                "description": "Get top N learners by score for a specific lab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier in format 'lab-01', 'lab-02', etc.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top learners to return (default: 5)",
                            "default": 5,
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_completion_rate",
                "description": "Get completion rate percentage for a specific lab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier in format 'lab-01', 'lab-02', etc.",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "trigger_sync",
                "description": "Trigger ETL sync to refresh data from the autochecker system",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
    ]


def get_system_prompt() -> str:
    """
    Get the system prompt for the LLM that encourages tool use.

    Returns:
        System prompt string
    """
    return """You are an AI assistant for a Learning Management System (LMS). Your job is to help users get information about labs, scores, pass rates, and student performance.

You have access to the following tools:
- get_items: List all labs and tasks
- get_learners: List all enrolled students
- get_scores: Get score distribution for a lab
- get_pass_rates: Get per-task pass rates for a lab
- get_timeline: Get submission timeline for a lab
- get_groups: Get per-group performance for a lab
- get_top_learners: Get top N learners for a lab
- get_completion_rate: Get completion rate for a lab
- trigger_sync: Refresh data from autochecker

When a user asks a question:
1. Use tools to gather the necessary data - ALWAYS call tools before answering
2. For questions comparing labs, call the tool for each lab and compare
3. For questions about "which lab has the lowest/highest", first get all labs with get_items, then get pass_rates for each
4. Format your response clearly with the data you found
5. If the user's message is a greeting or doesn't need data, respond naturally without tools

Be concise but informative. Always include relevant numbers from the data."""
