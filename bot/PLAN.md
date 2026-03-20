# Telegram Bot Development Plan

## Overview

This document outlines the development approach for the SE Toolkit Lab 7 Telegram bot, which provides students with access to their LMS scores, lab submissions, and course information through a conversational interface.

## Architecture

### 1. Project Scaffolding

The bot will be structured as a standalone Python package within the `bot/` directory, using `uv` for dependency management. This isolates the bot from the main application while allowing shared configuration through environment files.

### 2. Handler Architecture

Handlers are separated from the Telegram transport layer to enable testability:
- **Handlers** (`bot/handlers/`): Pure Python modules that process commands and return responses
- **Transport** (`bot/bot.py`): Telegram-specific code that forwards updates to handlers
- **Test Mode**: CLI interface that calls handlers directly without Telegram

### 3. Backend Integration

The bot integrates with:
- **LMS API** (`http://localhost:42002`): Fetches student scores and lab submissions
- **LLM API** (`http://localhost:42005/v1`): Provides natural language responses for complex queries

### 4. Intent Routing

Commands are routed based on user intent:
- `/start`, `/help` → Welcome and help messages
- `/health` → Bot health check
- `/scores` → Fetch and display student scores from LMS
- `/labs` → Show lab submission status

### 5. Deployment

The bot will be deployed on the VM using systemd or docker-compose, with environment variables loaded from `.env.bot.secret`. Health checks ensure the bot remains responsive.

## Implementation Phases

1. **Phase 1**: Scaffold project with `pyproject.toml` and basic handler structure
2. **Phase 2**: Implement test mode for CLI testing without Telegram
3. **Phase 3**: Add Telegram integration with aiogram
4. **Phase 4**: Implement LMS API integration for scores and labs
5. **Phase 5**: Deploy and verify in production
