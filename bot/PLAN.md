# Telegram Bot Development Plan

## Overview

This document outlines the development approach for the SE Toolkit Lab 7 Telegram bot, which provides students with access to their LMS scores, lab submissions, and course information through a conversational interface.

## Architecture

### 1. Project Scaffolding

The bot is structured as a standalone Python package within the `bot/` directory, using `uv` for dependency management. This isolates the bot from the main application while allowing shared configuration through environment files.

### 2. Handler Architecture

Handlers are separated from the Telegram transport layer to enable testability:
- **Handlers** (`bot/handlers/`): Pure Python modules that process commands and return responses
- **Transport** (`bot/bot.py`): Telegram-specific code that forwards updates to handlers
- **Test Mode**: CLI interface that calls handlers directly without Telegram

### 3. Backend Integration

The bot integrates with:
- **LMS API** (`http://localhost:42002`): Fetches student scores and lab submissions via 9 endpoints
- **LLM API** (`http://localhost:42005/v1`): Provides natural language understanding for intent routing

### 4. Intent Routing

The bot supports two routing modes:

**LLM-based routing (primary):**
- User message → LLM with tool definitions → API calls → LLM summarizes → Response
- The LLM receives tool schemas and decides which API calls to make
- Tool results are fed back to the LLM for multi-step reasoning

**Fallback routing (when LLM unavailable):**
- Keyword-based pattern matching for common queries
- Provides helpful responses even when LLM is down
- Not the primary routing method - just a safety net

### 5. Tool Definitions

All 9 backend endpoints are exposed as LLM tools:
- `get_items` - List all labs and tasks
- `get_learners` - List enrolled students
- `get_scores` - Score distribution for a lab
- `get_pass_rates` - Per-task pass rates
- `get_timeline` - Submission timeline
- `get_groups` - Per-group performance
- `get_top_learners` - Top N learners
- `get_completion_rate` - Completion percentage
- `trigger_sync` - Refresh data from autochecker

### 6. Deployment

The bot is deployed on the VM using systemd or docker-compose, with environment variables loaded from `.env.bot.secret`. Health checks ensure the bot remains responsive.

## Implementation Phases

1. **Phase 1**: Scaffold project with `pyproject.toml` and basic handler structure ✅
2. **Phase 2**: Implement test mode for CLI testing without Telegram ✅
3. **Phase 3**: Add Telegram integration with aiogram ✅
4. **Phase 4**: Implement LMS API integration for scores and labs ✅
5. **Phase 5**: Implement LLM-based intent routing with tool calling ✅
6. **Phase 6**: Add inline keyboard buttons for common actions ✅
7. **Phase 7**: Deploy and verify in production

## Current Status

All P0 and P1 requirements implemented:
- ✅ Testable handler architecture
- ✅ CLI test mode
- ✅ All 5 slash commands (/start, /help, /health, /labs, /scores)
- ✅ Error handling with user-friendly messages
- ✅ LLM-based intent routing with 9 tools
- ✅ Inline keyboard buttons
- ✅ Multi-step reasoning (finding lowest/highest pass rate labs)
- ✅ Fallback routing for LLM outages
