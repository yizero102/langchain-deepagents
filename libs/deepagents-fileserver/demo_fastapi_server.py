"""Demo script for FastAPI FileServer with security features.

This script demonstrates how to use the enhanced FastAPI-based file server
with authentication, rate limiting, and path traversal prevention.
"""

import os
import tempfile
from pathlib import Path

from fileserver import FastAPIFileServer


def demo_basic_server():
    """Demo: Start server with default settings."""
    print("=" * 80)
    print("Demo 1: Basic FastAPI Server")
    print("=" * 80)
    print("\nStarting server with default settings:")
    print("  - API Key authentication enabled (auto-generated)")
    print("  - Rate limiting: 100 requests per 60 seconds")
    print("  - Path traversal prevention enabled")
    print("\nNote: Copy the generated API key and use it in X-API-Key header")
    print()

    with tempfile.TemporaryDirectory() as temp_dir:
        server = FastAPIFileServer(
            root_dir=temp_dir,
            host="localhost",
            port=8080,
        )
        print(f"Root directory: {temp_dir}")
        print("\nTest the server with curl:")
        print("  # Health check (no auth required)")
        print("  curl http://localhost:8080/health")
        print()
        print("  # List files (requires API key)")
        print("  curl -H 'X-API-Key: YOUR_KEY_HERE' http://localhost:8080/api/ls")
        print()
        print("  # API Documentation")
        print("  Open http://localhost:8080/docs in your browser")
        print()
        server.start()


def demo_custom_api_key():
    """Demo: Start server with custom API key."""
    print("=" * 80)
    print("Demo 2: Custom API Key")
    print("=" * 80)
    print("\nStarting server with custom API key: 'my-secret-key-123'")
    print()

    with tempfile.TemporaryDirectory() as temp_dir:
        server = FastAPIFileServer(
            root_dir=temp_dir,
            host="localhost",
            port=8080,
            api_key="my-secret-key-123",
        )
        print(f"Root directory: {temp_dir}")
        print("\nTest the server with curl:")
        print("  curl -H 'X-API-Key: my-secret-key-123' http://localhost:8080/api/ls")
        print()
        server.start()


def demo_custom_rate_limiting():
    """Demo: Start server with custom rate limits."""
    print("=" * 80)
    print("Demo 3: Custom Rate Limiting")
    print("=" * 80)
    print("\nStarting server with strict rate limiting:")
    print("  - 10 requests per 30 seconds")
    print()

    with tempfile.TemporaryDirectory() as temp_dir:
        server = FastAPIFileServer(
            root_dir=temp_dir,
            host="localhost",
            port=8080,
            api_key="demo-key",
            enable_rate_limiting=True,
            rate_limit_requests=10,
            rate_limit_window=30,
        )
        print(f"Root directory: {temp_dir}")
        print("\nMake more than 10 requests in 30 seconds to see rate limiting:")
        print("  for i in {1..15}; do")
        print("    curl -H 'X-API-Key: demo-key' http://localhost:8080/api/ls")
        print('    echo "Request $i"')
        print("  done")
        print()
        server.start()


def demo_no_rate_limiting():
    """Demo: Start server without rate limiting."""
    print("=" * 80)
    print("Demo 4: No Rate Limiting")
    print("=" * 80)
    print("\nStarting server with rate limiting disabled:")
    print()

    with tempfile.TemporaryDirectory() as temp_dir:
        server = FastAPIFileServer(
            root_dir=temp_dir,
            host="localhost",
            port=8080,
            api_key="demo-key",
            enable_rate_limiting=False,
        )
        print(f"Root directory: {temp_dir}")
        print("\nRate limiting is disabled - make unlimited requests!")
        print()
        server.start()


def print_usage_examples():
    """Print usage examples with curl and Python."""
    print("=" * 80)
    print("FastAPI FileServer Usage Examples")
    print("=" * 80)
    print()

    print("1. Using curl:")
    print("-" * 40)
    print()
    print("# Health check (no auth required)")
    print("curl http://localhost:8080/health")
    print()
    print("# List directory")
    print("curl -H 'X-API-Key: YOUR_KEY' http://localhost:8080/api/ls?path=/tmp")
    print()
    print("# Read file")
    print("curl -H 'X-API-Key: YOUR_KEY' http://localhost:8080/api/read?file_path=test.txt")
    print()
    print("# Write file")
    print("curl -X POST http://localhost:8080/api/write \\")
    print("  -H 'X-API-Key: YOUR_KEY' \\")
    print("  -H 'Content-Type: application/json' \\")
    print('  -d \'{"file_path": "test.txt", "content": "Hello World"}\'')
    print()
    print("# Edit file")
    print("curl -X POST http://localhost:8080/api/edit \\")
    print("  -H 'X-API-Key: YOUR_KEY' \\")
    print("  -H 'Content-Type: application/json' \\")
    print('  -d \'{"file_path": "test.txt", "old_string": "World", "new_string": "Python"}\'')
    print()
    print("# Search for pattern")
    print("curl -H 'X-API-Key: YOUR_KEY' 'http://localhost:8080/api/grep?pattern=TODO&path=/tmp'")
    print()
    print("# Glob pattern")
    print("curl -H 'X-API-Key: YOUR_KEY' 'http://localhost:8080/api/glob?pattern=*.py&path=/tmp'")
    print()

    print("2. Using Python requests:")
    print("-" * 40)
    print()
    print("""
import requests

BASE_URL = "http://localhost:8080"
API_KEY = "YOUR_KEY_HERE"
headers = {"X-API-Key": API_KEY}

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Write a file
response = requests.post(
    f"{BASE_URL}/api/write",
    json={"file_path": "test.txt", "content": "Hello World"},
    headers=headers
)
print(response.json())

# Read the file
response = requests.get(
    f"{BASE_URL}/api/read",
    params={"file_path": "test.txt"},
    headers=headers
)
print(response.json())

# Edit the file
response = requests.post(
    f"{BASE_URL}/api/edit",
    json={"file_path": "test.txt", "old_string": "World", "new_string": "Python"},
    headers=headers
)
print(response.json())

# Search for pattern
response = requests.get(
    f"{BASE_URL}/api/grep",
    params={"pattern": "Hello"},
    headers=headers
)
print(response.json())
    """)

    print()
    print("3. API Documentation:")
    print("-" * 40)
    print()
    print("Open http://localhost:8080/docs in your browser to see:")
    print("  - Interactive API documentation (Swagger UI)")
    print("  - Try out endpoints directly from the browser")
    print("  - View request/response schemas")
    print()

    print("4. Security Features:")
    print("-" * 40)
    print()
    print("✓ API Key Authentication:")
    print("  - All endpoints (except /health) require X-API-Key header")
    print("  - Custom or auto-generated API keys")
    print()
    print("✓ Rate Limiting:")
    print("  - Configurable requests per time window")
    print("  - Returns 429 status when limit exceeded")
    print()
    print("✓ Path Traversal Prevention:")
    print("  - All paths are validated and resolved safely")
    print("  - Cannot access files outside root directory")
    print()
    print("✓ Input Validation:")
    print("  - Pydantic models validate all request data")
    print("  - Returns 422 for invalid inputs")
    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        demo = sys.argv[1]
        if demo == "1":
            demo_basic_server()
        elif demo == "2":
            demo_custom_api_key()
        elif demo == "3":
            demo_custom_rate_limiting()
        elif demo == "4":
            demo_no_rate_limiting()
        else:
            print("Invalid demo number. Choose 1-4.")
            sys.exit(1)
    else:
        print_usage_examples()
        print()
        print("To run a demo:")
        print("  python demo_fastapi_server.py 1  # Basic server with auto-generated API key")
        print("  python demo_fastapi_server.py 2  # Custom API key")
        print("  python demo_fastapi_server.py 3  # Custom rate limiting")
        print("  python demo_fastapi_server.py 4  # No rate limiting")
        print()
