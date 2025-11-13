# Dockerfile for DeepAgents FileServer
# Supports both standard and FastAPI server modes

FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Copy package files
COPY pyproject.toml ./
COPY fileserver ./fileserver
COPY README.md ./

# Install Python dependencies
# Use --no-deps and install dependencies manually to avoid network issues
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir fastapi uvicorn[standard] pydantic && \
    pip install --no-cache-dir --no-deps -e .

# Create data directory for file operations
RUN mkdir -p /data

# Expose default port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FILESERVER_ROOT_DIR=/data
ENV FILESERVER_HOST=0.0.0.0
ENV FILESERVER_PORT=8080
ENV FILESERVER_MODE=fastapi

# Add healthcheck using Python
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()" || exit 1

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
