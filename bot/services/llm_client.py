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
                timeout=120.0,  # 2 minute timeout for LLM responses
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
        tool_choice: Optional[str] = "auto",
    ) -> dict:
        """
        Send messages to the LLM and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions for function calling
            tool_choice: How to use tools ("auto", "required", or "none"). Only used if tools is provided.

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
            if tool_choice:
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
                raise RuntimeError(f"LLM API authentication failed (401). Token may have expired. Response: {e.response.text[:200]}")
            raise RuntimeError(f"LLM API error: HTTP {e.response.status_code} {e.response.reason_phrase}. Response: {e.response.text[:200]}")
        except httpx.ConnectError as e:
            raise RuntimeError(f"LLM connection refused ({self.base_url}). Check that the LLM service is running.")
        except httpx.HTTPError as e:
            raise RuntimeError(f"LLM API HTTP error: {type(e).__name__}: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"LLM API unexpected error: {type(e).__name__}: {str(e)}")

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

            # Only send tools on the first iteration - the proxy rejects tools on subsequent calls
            # after tool results are returned
            include_tools = tools if iteration == 0 else None
            try:
                result = await self.chat(messages, tools=include_tools, tool_choice="auto" if include_tools else None)
            except Exception as e:
                if debug:
                    print(f"[chat error] Iteration {iteration + 1}: {type(e).__name__}: {e}", file=sys.stderr)
                raise

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
            # Construct assistant message with tool_calls for proper OpenAI-compatible format
            assistant_message = {
                "role": "assistant",
                "content": result.get("content", ""),
            }
            # Include tool_calls in the assistant message if present
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            
            messages.append(assistant_message)
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
            Tool execution result or error message for the LLM
        """
        from services.lms_client import LmsClient

        client = LmsClient()
        try:
            # Get the method by name
            method = getattr(client, name, None)
            if not method:
                return {"error": f"Unknown tool: {name}. Available tools: get_items, get_learners, get_scores, get_pass_rates, get_timeline, get_groups, get_top_learners, get_completion_rate, trigger_sync"}

            # Check for required 'lab' parameter
            tools_requiring_lab = ["get_scores", "get_pass_rates", "get_timeline", "get_groups", "get_top_learners", "get_completion_rate"]
            if name in tools_requiring_lab:
                if not arguments or "lab" not in arguments:
                    return {"error": f"Missing required 'lab' parameter. You must provide a lab ID like 'lab-01', 'lab-02', etc. Call get_items first to get valid lab IDs, then call {name}(lab='lab-XX') with the specific lab ID."}
                # Validate lab ID format
                lab_id = arguments.get("lab", "")
                if not lab_id.startswith("lab-"):
                    return {"error": f"Invalid lab ID format: '{lab_id}'. Lab IDs must be in format 'lab-01', 'lab-02', etc. Call get_items first to get valid lab IDs."}

            # Call the method with arguments
            if arguments:
                result = await method(**arguments)
            else:
                result = await method()

            return result
        except TypeError as e:
            # Handle missing/incorrect arguments
            error_msg = str(e)
            if "missing" in error_msg and "required" in error_msg:
                return {"error": f"Missing required argument: {error_msg}. For lab-specific tools, you must provide lab='lab-01', 'lab-02', etc. Call get_items first to get valid lab IDs."}
            return {"error": f"Invalid arguments: {error_msg}"}
        except Exception as e:
            return {"error": f"Tool execution error: {str(e)}"}
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
                "description": "Get list of all labs and tasks available in the system. Use this first to get lab IDs before calling other tools. No parameters required.",
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
                "description": "Get list of all enrolled learners/students. No parameters required.",
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
                "description": "Get score distribution (4 buckets) for a specific lab. You MUST provide a lab ID from get_items results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "REQUIRED. Lab identifier like 'lab-01', 'lab-02', 'lab-03', etc. Get valid IDs from get_items first.",
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
                "description": "Get per-task average scores and attempt counts for a specific lab. You MUST provide a lab ID from get_items results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "REQUIRED. Lab identifier like 'lab-01', 'lab-02', 'lab-03', etc. Get valid IDs from get_items first.",
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
                "description": "Get submission timeline (submissions per day) for a specific lab. You MUST provide a lab ID from get_items results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "REQUIRED. Lab identifier like 'lab-01', 'lab-02', 'lab-03', etc. Get valid IDs from get_items first.",
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
                "description": "Get per-group performance scores and student counts for a specific lab. You MUST provide a lab ID from get_items results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "REQUIRED. Lab identifier like 'lab-01', 'lab-02', 'lab-03', etc. Get valid IDs from get_items first.",
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
                "description": "Get top N learners by score for a specific lab. You MUST provide a lab ID from get_items results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "REQUIRED. Lab identifier like 'lab-01', 'lab-02', 'lab-03', etc. Get valid IDs from get_items first.",
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
                "description": "Get completion rate percentage for a specific lab. You MUST provide a lab ID from get_items results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "REQUIRED. Lab identifier like 'lab-01', 'lab-02', 'lab-03', etc. Get valid IDs from get_items first.",
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
                "description": "Trigger ETL sync to refresh data from the autochecker system. Use this when user asks to 'sync', 'refresh', 'update', or 'reload' data. No parameters required.",
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
- get_items: List all labs and tasks (no parameters needed)
- get_learners: List all enrolled students (no parameters needed)
- get_scores: Get score distribution for a specific lab (requires lab parameter)
- get_pass_rates: Get per-task pass rates for a specific lab (requires lab parameter)
- get_timeline: Get submission timeline for a specific lab (requires lab parameter)
- get_groups: Get per-group performance for a specific lab (requires lab parameter)
- get_top_learners: Get top N learners for a specific lab (requires lab parameter)
- get_completion_rate: Get completion rate for a specific lab (requires lab parameter)
- trigger_sync: Refresh data from autochecker (no parameters needed) - use for "sync", "refresh", "update", "reload" queries

CRITICAL RULES:
1. ALWAYS call tools before answering - never guess or make up data
2. For tools requiring a "lab" parameter, you MUST provide a valid lab ID like "lab-01", "lab-02", etc.
3. To get lab IDs, first call get_items, then extract the lab identifiers from the results
4. For "which lab has the lowest/highest" questions: call get_items first, then call get_pass_rates for EACH lab with its specific lab ID
5. For sync/refresh/update queries: call trigger_sync immediately
6. Always include specific numbers in your response (percentages, counts, lab names)
7. Format your answer clearly with the actual data you retrieved

Example workflow for "which lab has the lowest pass rate?":
1. Call get_items() → get list of labs
2. For each lab ID (e.g., "lab-01", "lab-02"), call get_pass_rates(lab="lab-01")
3. Compare the results and report the lab with lowest average, including the percentage

Example workflow for "sync the data":
1. Call trigger_sync()
2. Report success with details from the response

Be concise but informative. Always include relevant numbers from the data."""
