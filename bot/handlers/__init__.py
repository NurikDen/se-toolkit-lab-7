"""
Command handlers for the SE Toolkit Lab 7 Telegram bot.

Handlers are separated from the Telegram transport layer to enable
testability. They can be called directly in test mode without Telegram.
"""

from .commands import (
    COMMAND_HANDLERS,
    handle_help,
    handle_health,
    handle_labs,
    handle_scores,
    handle_start,
    route_command,
)

__all__ = [
    "COMMAND_HANDLERS",
    "handle_help",
    "handle_health",
    "handle_labs",
    "handle_scores",
    "handle_start",
    "route_command",
]
