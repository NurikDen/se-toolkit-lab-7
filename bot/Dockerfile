# SE Toolkit Lab 7 Telegram Bot
# Uses uv for dependency management (not pip/requirements.txt)

FROM python:3.12-slim

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy bot source code
COPY bot.py config.py ./
COPY handlers/ ./handlers/
COPY services/ ./services/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the bot
CMD ["uv", "run", "python", "bot.py"]
