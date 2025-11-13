FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    ROOT_DIR=/data \
    SERVER_TYPE=fastapi \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN useradd -m -u 1000 fileserver && \
    mkdir -p /data && \
    chown -R fileserver:fileserver /data

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    pydantic>=2.0.0

# Copy application code
COPY --chown=fileserver:fileserver fileserver ./fileserver
COPY --chown=fileserver:fileserver pyproject.toml .

# Switch to non-root user
USER fileserver

# Create volume mount point
VOLUME ["/data"]

# Expose default port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health').read()" || exit 1

# Entrypoint script to handle both server types
ENTRYPOINT ["sh", "-c", "if [ \"$SERVER_TYPE\" = \"standard\" ]; then python -m fileserver.server ${ROOT_DIR} ${PORT}; else python -m fileserver.server_fastapi ${ROOT_DIR} ${PORT}; fi"]
