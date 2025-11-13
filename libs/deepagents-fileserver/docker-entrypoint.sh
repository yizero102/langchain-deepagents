#!/bin/bash
set -e

# Default values
ROOT_DIR="${FILESERVER_ROOT_DIR:-/data}"
HOST="${FILESERVER_HOST:-0.0.0.0}"
PORT="${FILESERVER_PORT:-8080}"
MODE="${FILESERVER_MODE:-fastapi}"
API_KEY="${FILESERVER_API_KEY:-}"

# Ensure root directory exists
mkdir -p "$ROOT_DIR"

echo "==================================="
echo "DeepAgents FileServer Docker"
echo "==================================="
echo "Mode:       $MODE"
echo "Root Dir:   $ROOT_DIR"
echo "Host:       $HOST"
echo "Port:       $PORT"
echo "==================================="

# Run the appropriate server
if [ "$MODE" = "fastapi" ]; then
    echo "Starting FastAPI Server..."
    if [ -n "$API_KEY" ]; then
        echo "Using provided API key"
        export FILESERVER_API_KEY="$API_KEY"
    else
        echo "API key will be auto-generated"
    fi
    exec python -m fileserver.server_fastapi "$ROOT_DIR" "$PORT"
elif [ "$MODE" = "standard" ]; then
    echo "Starting Standard Server..."
    exec python -m fileserver.server "$ROOT_DIR" "$PORT"
else
    echo "ERROR: Invalid FILESERVER_MODE: $MODE"
    echo "Valid modes: fastapi, standard"
    exit 1
fi
