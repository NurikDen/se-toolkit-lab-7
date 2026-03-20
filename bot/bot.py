#!/usr/bin/env python3
"""
SE Toolkit Lab 7 Telegram Bot

Entry point with support for:
- Production mode: Runs as a Telegram bot using aiogram
- Test mode (--test): Calls handlers directly without Telegram
"""

import argparse
import asyncio
import sys

from config import load_config
from handlers import route_command

# Load configuration from .env.bot.secret
load_config()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SE Toolkit Lab 7 Telegram Bot"
    )
    parser.add_argument(
        "--test",
        type=str,
        metavar="COMMAND",
        help="Test mode: run a command directly (e.g., --test '/start')"
    )
    return parser.parse_args()


async def run_test_mode(command: str) -> int:
    """
    Run bot in test mode - call handler directly without Telegram.
    
    Args:
        command: The command to test (e.g., "/start", "/help")
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Strip leading slash if present
        cmd = command.lstrip("/")
        
        # Route command to handler
        response = await route_command(cmd)
        
        # Print response to stdout
        print(response)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def run_production_mode() -> None:
    """Run bot in production mode with Telegram integration."""
    try:
        from aiogram import Bot, Dispatcher, types
        from aiogram.filters import Command
    except ImportError:
        print(
            "Error: aiogram not installed. Run 'uv sync' in the bot directory.",
            file=sys.stderr
        )
        sys.exit(1)

    from config import BOT_TOKEN

    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not set in environment", file=sys.stderr)
        sys.exit(1)

    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Register command handlers
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        response = await route_command("start", message.from_user.id)
        await message.answer(response)
    
    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        response = await route_command("help", message.from_user.id)
        await message.answer(response)
    
    @dp.message(Command("health"))
    async def cmd_health(message: types.Message):
        response = await route_command("health", message.from_user.id)
        await message.answer(response)
    
    @dp.message(Command("scores"))
    async def cmd_scores(message: types.Message):
        response = await route_command("scores", message.from_user.id)
        await message.answer(response)
    
    @dp.message(Command("labs"))
    async def cmd_labs(message: types.Message):
        response = await route_command("labs", message.from_user.id)
        await message.answer(response)
    
    # Start polling
    print("Bot is starting...")
    await dp.start_polling(bot)


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    if args.test:
        # Test mode: run command directly
        return asyncio.run(run_test_mode(args.test))
    else:
        # Production mode: run Telegram bot
        asyncio.run(run_production_mode())
        return 0


if __name__ == "__main__":
    sys.exit(main())
