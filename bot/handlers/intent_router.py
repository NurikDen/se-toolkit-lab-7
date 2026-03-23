"""
Intent router for natural language queries.

Routes user messages to LLM with tool definitions for LMS API access.
The LLM decides which tools to call based on the user's intent.
"""

import sys
from typing import Optional

from services.lms_client import LmsClient
from services.llm_client import LlmClient, get_system_prompt, get_tool_definitions


def is_greeting(message: str) -> bool:
    """Check if message is a simple greeting."""
    greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    return message.lower().strip() in greetings


def is_sync_request(message: str) -> bool:
    """Check if message is requesting a data sync."""
    sync_keywords = ["sync", "refresh", "update", "reload", "load data", "fetch data"]
    message_lower = message.lower().strip()
    return any(keyword in message_lower for keyword in sync_keywords)


def get_greeting_response(message: str) -> str:
    """Return a friendly greeting response with capabilities hint."""
    return (
        "Hello! 👋 I'm your SE Toolkit Lab 7 assistant. "
        "I can help you with:\n\n"
        "- Viewing available labs and tasks\n"
        "- Checking pass rates and scores for labs\n"
        "- Finding top learners and group performance\n"
        "- Tracking submission timelines\n\n"
        "Just ask me anything like:\n"
        "• 'What labs are available?'\n"
        "• 'Show me scores for lab 4'\n"
        "• 'Which lab has the lowest pass rate?'\n"
        "• 'Who are the top 5 students in lab 3?'\n"
        "• 'Sync the data' - refresh data from autochecker"
    )


async def route_intent(message: str, user_id: Optional[int] = None, debug: bool = True) -> str:
    """
    Route a natural language message using LLM with tool calling.

    The LLM receives:
    - The user's message
    - A system prompt explaining its role
    - Tool definitions for all 9 LMS API endpoints

    The LLM decides which tools to call, we execute them,
    feed results back, and the LLM produces the final answer.

    Args:
        message: User's message text
        user_id: Optional Telegram user ID
        debug: Whether to print debug info to stderr

    Returns:
        Response text
    """
    # Handle greetings without calling LLM (simple pattern, not routing)
    if is_greeting(message):
        return get_greeting_response(message)

    # Handle sync requests explicitly to ensure trigger_sync is called
    if is_sync_request(message):
        # Pre-process sync requests to ensure the LLM calls trigger_sync
        message = f"[SYNC REQUEST] {message}. Please call trigger_sync to sync/refresh the data from autochecker."

    # Get tool definitions and system prompt
    tools = get_tool_definitions()
    system_prompt = get_system_prompt()

    # Create LLM client
    llm = LlmClient()

    try:
        # Use the LLM's chat_with_tools method which handles the tool calling loop
        response = await llm.chat_with_tools(
            user_message=message,
            tools=tools,
            system_prompt=system_prompt,
            max_iterations=5,
            debug=debug,
        )
        return response
    except RuntimeError as e:
        # LLM unavailable - return helpful error message
        error_msg = str(e)
        if debug:
            print(f"[error] LLM unavailable: {error_msg}", file=sys.stderr)
        return (
            "I'm having trouble connecting to my brain right now (LLM service unavailable).\n\n"
            "You can still use slash commands:\n"
            "/start - Welcome message\n"
            "/help - List of commands\n"
            "/health - Check backend status\n"
            "/labs - List available labs\n"
            "/scores <lab> - View pass rates (e.g., /scores lab-04)\n\n"
            f"Technical details: {error_msg}"
        )
    except Exception as e:
        if debug:
            print(f"[error] Unexpected error: {e}", file=sys.stderr)
        return f"Sorry, I encountered an error: {str(e)}"
    finally:
        await llm.close()
