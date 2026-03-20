"""
Core command handlers for the SE Toolkit Lab 7 Telegram bot.

Handlers are separated from the Telegram transport layer to enable
testability. They can be called directly in test mode without Telegram.
"""

import os
from typing import Optional

# LLM API configuration
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "http://localhost:42005/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_MODEL = os.getenv("LLM_API_MODEL", "coder-model")

# LMS API configuration
LMS_API_URL = os.getenv("LMS_API_URL", "http://localhost:42002")
LMS_API_KEY = os.getenv("LMS_API_KEY", "")


async def handle_start(user_id: Optional[int] = None) -> str:
    """Handle /start command - welcome message."""
    return (
        "👋 Welcome to SE Toolkit Lab 7 Bot!\n\n"
        "I can help you check your scores and lab submissions.\n\n"
        "Available commands:\n"
        "/start - Show this welcome message\n"
        "/help - Show help information\n"
        "/health - Check bot health status\n"
        "/scores - View your current scores\n"
        "/labs - Check lab submission status"
    )


async def handle_help(user_id: Optional[int] = None) -> str:
    """Handle /help command - help information."""
    return (
        "📚 SE Toolkit Lab 7 Bot Help\n\n"
        "This bot provides access to your LMS data through Telegram.\n\n"
        "**Commands:**\n"
        "/start - Welcome message and bot introduction\n"
        "/help - This help message\n"
        "/health - Bot health check\n"
        "/scores - Fetch and display your current scores from LMS\n"
        "/labs - Show your lab submission status\n\n"
        "**Tips:**\n"
        "- Scores are fetched from the LMS API\n"
        "- Lab submissions show completion status\n"
        "- All data is specific to your Telegram account"
    )


async def handle_health(user_id: Optional[int] = None) -> str:
    """Handle /health command - bot health check."""
    return (
        "✅ Bot is healthy!\n\n"
        f"LLM API: {LLM_API_BASE_URL}\n"
        f"LMS API: {LMS_API_URL}\n"
        "Status: All systems operational"
    )


async def handle_scores(user_id: Optional[int] = None) -> str:
    """Handle /scores command - fetch and display scores."""
    # Placeholder - will be implemented with LMS API integration
    return (
        "📊 Your Current Scores\n\n"
        "Scores are being fetched from the LMS...\n\n"
        "_Note: This is a placeholder response. "
        "LMS API integration will be added in Phase 4._"
    )


async def handle_labs(user_id: Optional[int] = None) -> str:
    """Handle /labs command - show lab submission status."""
    # Placeholder - will be implemented with LMS API integration
    return (
        "📝 Lab Submissions\n\n"
        "Lab submission status:\n"
        "- Lab 1: ✅ Submitted\n"
        "- Lab 2: ⏳ In Progress\n"
        "- Lab 3: 📋 Not Started\n\n"
        "_Note: This is a placeholder response. "
        "LMS API integration will be added in Phase 4._"
    )


# Command router - maps command names to handler functions
COMMAND_HANDLERS = {
    "start": handle_start,
    "help": handle_help,
    "health": handle_health,
    "scores": handle_scores,
    "labs": handle_labs,
}


async def route_command(command: str, user_id: Optional[int] = None) -> str:
    """
    Route a command to the appropriate handler.

    Args:
        command: The command name (without the / prefix)
        user_id: Optional telegram user ID

    Returns:
        Response text from the handler
    """
    handler = COMMAND_HANDLERS.get(command.lower())
    if handler:
        return await handler(user_id)
    return f"❓ Unknown command: /{command}\nUse /help to see available commands."
