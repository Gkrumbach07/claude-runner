# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18+ (required for Claude Code)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Claude Code CLI and MCP servers globally
RUN npm install -g @anthropic-ai/claude-code @playwright/mcp

# Install Playwright browsers for MCP
RUN npx playwright install chromium --with-deps

# Create a non-root user FIRST
RUN useradd --create-home --shell /bin/bash --uid 1000 claude

# Switch to claude user to set up Claude Code properly
USER claude

# Create required directories for Claude Code
RUN mkdir -p /home/claude/.config/claude \
    && mkdir -p /home/claude/.local/share/claude \
    && mkdir -p /home/claude/.cache/claude

# Copy the application files
COPY --chown=claude:claude main.py /app/
COPY --chown=claude:claude CLAUDE.md /app/
COPY --chown=claude:claude .mcp.json /app/

# Make the script executable
RUN chmod +x /app/main.py

# Initialize Claude Code with API key (this creates necessary auth state)
# We'll do this at runtime when we have the actual API key

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NODE_OPTIONS="--max-old-space-size=2048"
ENV HOME=/home/claude
ENV USER=claude
ENV SHELL=/bin/bash
ENV TERM=xterm-256color

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the application
CMD ["python", "main.py"]