"""
Configuration loader for the SE Toolkit Lab 7 Telegram bot.

Loads environment variables from .env.bot.secret or .env.bot.example.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_config() -> None:
    """
    Load environment variables from .env.bot.secret file.
    
    Tries the following paths in order:
    1. bot/.env.bot.secret
    2. .env.bot.secret (parent directory)
    3. bot/.env.bot.example (fallback for development)
    """
    # Get the bot directory (where this file is located)
    bot_dir = Path(__file__).parent
    
    # Try bot/.env.bot.secret first
    env_path = bot_dir / ".env.bot.secret"
    if env_path.exists():
        load_dotenv(env_path)
        return
    
    # Try parent directory .env.bot.secret
    parent_env_path = bot_dir.parent / ".env.bot.secret"
    if parent_env_path.exists():
        load_dotenv(parent_env_path)
        return
    
    # Fallback to .env.bot.example for development
    example_path = bot_dir / ".env.bot.example"
    if example_path.exists():
        load_dotenv(example_path)
        return


# Configuration values (loaded from environment)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
LMS_API_URL = os.getenv("LMS_API_URL", "http://localhost:42002")
LMS_API_KEY = os.getenv("LMS_API_KEY", "")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "http://localhost:42005/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_MODEL = os.getenv("LLM_API_MODEL", "coder-model")
