# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies + debugging tools
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    gnupg \
    strace \
    procps \
    lsof \
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

# Install Playwright system dependencies as root FIRST
RUN npx playwright install-deps chromium

# Create a non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 claude

# Switch to claude user to set up Claude Code properly  
USER claude

# Create required directories for Claude Code
RUN mkdir -p /home/claude/.config/claude \
    && mkdir -p /home/claude/.local/share/claude \
    && mkdir -p /home/claude/.cache/claude

# Install Playwright browsers as claude user (system deps already installed)
ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/.cache/ms-playwright
RUN mkdir -p /tmp/.cache/ms-playwright && \
    npx playwright install chromium && \
    echo "Browser installation completed for claude user" && \
    ls -la /tmp/.cache/ms-playwright/ && \
    npx playwright install --dry-run chromium

# Switch back to root to set permissions and verify installation
USER root
RUN chmod -R 755 /tmp/.cache/ms-playwright && \
    find /tmp/.cache/ms-playwright -name "chromium*" -type f -exec chmod +x {} \; && \
    ls -la /tmp/.cache/ms-playwright/ && \
    echo "Browser permissions set successfully"

# Create additional required directories with proper permissions
RUN mkdir -p /tmp/.config /tmp/.cache /tmp/.local/share /tmp/.playwright-profile /tmp/.playwright-mcp-work && \
    chmod -R 777 /tmp/.config /tmp/.cache /tmp/.local /tmp/.playwright-profile /tmp/.playwright-mcp-work && \
    mkdir -p /app/.playwright-mcp && \
    chown -R claude:claude /app/.playwright-mcp && \
    chmod -R 755 /app/.playwright-mcp

# Install virtual display for headless mode (optional, for better compatibility)
RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

# Create startup script for virtual display
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &\nexport DISPLAY=:99\nexec "$@"' > /usr/local/bin/start-xvfb && \
    chmod +x /usr/local/bin/start-xvfb

USER claude

# Verify browser installation works with headless test
RUN npx playwright --version && \
    echo "Playwright CLI verification successful" && \
    timeout 30s npx @playwright/mcp --headless --browser chromium --help || echo "MCP server help completed"

# Copy the application files
COPY --chown=claude:claude main.py /app/
COPY --chown=claude:claude CLAUDE.md /app/

# Switch to claude user for setup
USER claude

# Ensure browser is accessible and install if needed for MCP server
RUN export PLAYWRIGHT_BROWSERS_PATH=/tmp/.cache/ms-playwright && \
    npx playwright install chromium --force && \
    echo "Browser re-installed for MCP compatibility"

# Register MCP server at USER scope only (works for both CLI and SDK)
RUN cd /app && claude mcp add playwright \
    --command "npx" \
    --args "@playwright/mcp --headless --browser chromium --user-data-dir /tmp/.playwright-profile --isolated" \
    --env "PLAYWRIGHT_BROWSERS_PATH=/tmp/.cache/ms-playwright" \
    --env "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=false" \
    --env "PW_CHROMIUM_ARGS=--no-sandbox --disable-gpu --disable-dev-shm-usage --disable-extensions --disable-plugins --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-renderer-backgrounding" \
    --env "DEBUG=pw:api" \
    --env "DISPLAY=:99" \
    --env "PLAYWRIGHT_MCP_WORK_DIR=/tmp/.playwright-mcp-work" \
    --env "TMPDIR=/tmp" \
    --env "TMP=/tmp" \
    --env "HOME=/tmp" \
    --scope local

# Verify registration
RUN claude mcp list && echo "MCP server registered successfully"

# Make the script executable (as claude user)
RUN chmod +x /app/main.py

# Switch back to root for system-level setup
USER root

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NODE_OPTIONS="--max-old-space-size=2048"
ENV HOME=/home/claude
ENV USER=claude
ENV SHELL=/bin/bash
ENV TERM=xterm-256color

# Playwright configuration for containers
ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/.cache/ms-playwright
ENV PW_CHROMIUM_ARGS="--no-sandbox --disable-gpu"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Set API key environment for SDK
ENV ANTHROPIC_API_KEY=""

# Switch back to claude user for runtime
USER claude

# Run the application with virtual display
CMD ["start-xvfb", "python", "main.py"]