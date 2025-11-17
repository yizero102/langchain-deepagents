# Multi-stage Dockerfile for DeepAgents FileServer
# Supports both standard and FastAPI servers

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    pydantic>=2.0.0

# Copy application code
COPY fileserver/ ./fileserver/

# Create a directory for file operations (can be mounted as volume)
RUN mkdir -p /data

# Set default working directory for file operations
WORKDIR /data

# Expose default port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()" || exit 1

# Default to FastAPI server (recommended)
# Can be overridden at runtime:
# - For standard server: docker run ... python -m fileserver.server
# - For FastAPI server: docker run ... python -m fileserver.server_fastapi
ENTRYPOINT ["python", "-m"]
CMD ["fileserver.server_fastapi", "/data", "8080"]
