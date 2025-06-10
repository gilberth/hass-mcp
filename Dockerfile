# MCP server Dockerfile for Claude Desktop integration
FROM ghcr.io/astral-sh/uv:0.6.6-python3.13-bookworm

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Set environment for MCP communication
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# --- BEGIN NETWORK MODE CONFIGURATION ---
# Set the default run mode to network
ENV HASS_MCP_RUN_MODE=network
# Set the default host and port for network mode
ENV HASS_MCP_HOST=0.0.0.0
ENV HASS_MCP_PORT=8008
# Expose the port
EXPOSE 8008
# --- END NETWORK MODE CONFIGURATION ---

# Install package with UV (using --system flag)
RUN uv pip install --system -e .

# Run the MCP server with stdio communication using the module directly
# The __main__.py script will now check HASS_MCP_RUN_MODE
ENTRYPOINT ["python", "-m", "app"]
