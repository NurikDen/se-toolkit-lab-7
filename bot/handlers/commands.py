"""
Core command handlers for the SE Toolkit Lab 7 Telegram bot.

Handlers are separated from the Telegram transport layer to enable
testability. They can be called directly in test mode without Telegram.
"""

from typing import Optional

from services.lms_client import LmsClient


async def handle_start(user_id: Optional[int] = None) -> str:
    """Handle /start command - welcome message."""
    return (
        "👋 Welcome to SE Toolkit Lab 7 Bot!\n\n"
        "I can help you check your scores and lab submissions.\n\n"
        "Available commands:\n"
        "/start - Show this welcome message\n"
        "/help - Show help information\n"
        "/health - Check bot health status\n"
        "/scores <lab> - View pass rates for a lab\n"
        "/labs - List available labs"
    )


async def handle_help(user_id: Optional[int] = None) -> str:
    """Handle /help command - help information."""
    return (
        "📚 SE Toolkit Lab 7 Bot Help\n\n"
        "This bot provides access to your LMS data through Telegram.\n\n"
        "**Commands:**\n"
        "/start - Welcome message and bot introduction\n"
        "/help - This help message\n"
        "/health - Check backend health status\n"
        "/labs - List all available labs\n"
        "/scores <lab> - Show pass rates for a specific lab (e.g., /scores lab-04)\n\n"
        "**Tips:**\n"
        "- All data is fetched from the LMS backend\n"
        "- Use /health to check if the backend is running\n"
        "- Lab IDs are in the format 'lab-01', 'lab-02', etc."
    )


async def handle_health(user_id: Optional[int] = None) -> str:
    """Handle /health command - bot health check."""
    client = LmsClient()
    try:
        result = await client.health_check()
        return f"Backend is healthy. {result['item_count']} items available."
    except RuntimeError as e:
        return f"Backend error: {str(e)}"
    finally:
        await client.close()


async def handle_scores(arg: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """
    Handle /scores command - fetch and display pass rates.

    Args:
        arg: The lab identifier (e.g., "lab-04") or None
        user_id: Optional telegram user ID
    """
    if not arg:
        return "Usage: /scores <lab>\n\nExample: /scores lab-04\n\nUse /labs to see available labs."

    client = LmsClient()
    try:
        pass_rates = await client.get_pass_rates(arg)
        if not pass_rates:
            return f"No pass rate data found for '{arg}'."

        # Format the response
        lines = [f"Pass rates for {arg}:"]
        for rate in pass_rates:
            task = rate.get("task", "Unknown")
            avg_score = rate.get("avg_score", 0)
            attempts = rate.get("attempts", 0)
            lines.append(f"- {task}: {avg_score}% ({attempts} attempts)")

        return "\n".join(lines)
    except RuntimeError as e:
        return f"Backend error: {str(e)}"
    finally:
        await client.close()


async def handle_labs(user_id: Optional[int] = None) -> str:
    """Handle /labs command - show available labs."""
    client = LmsClient()
    try:
        items = await client.get_items()
        # Filter only labs (not tasks)
        labs = [item for item in items if item.get("type") == "lab"]

        if not labs:
            return "No labs found."

        # Format the response
        lines = ["Available labs:"]
        for lab in labs:
            lab_id = lab.get("id", "")
            title = lab.get("title", "Unknown")
            lines.append(f"- {title}")

        return "\n".join(lines)
    except RuntimeError as e:
        return f"Backend error: {str(e)}"
    finally:
        await client.close()


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
        command: The command name (without the / prefix), may include arguments
        user_id: Optional telegram user ID

    Returns:
        Response text from the handler
    """
    # Split command and arguments
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else None

    handler = COMMAND_HANDLERS.get(cmd)
    if handler:
        # Pass arg for scores, user_id for all
        if cmd == "scores":
            return await handler(arg, user_id)
        return await handler(user_id)
    return f"❓ Unknown command: /{cmd}\nUse /help to see available commands."
