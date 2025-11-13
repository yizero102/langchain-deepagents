"""Demo script to verify FileServer functionality.

This script demonstrates all the key features of the FileServer:
1. Starting the server
2. Making HTTP requests to test all endpoints
3. Verifying operations work correctly
"""

import json
import os
import shutil
import tempfile
import threading
import time
from http.client import HTTPConnection
from pathlib import Path

from fileserver import FileServer


def make_request(client, method, path, body=None):
    """Helper to make HTTP requests and parse JSON responses."""
    headers = {"Content-Type": "application/json"} if body else {}
    if body:
        body_data = json.dumps(body).encode("utf-8")
        headers["Content-Length"] = str(len(body_data))
        client.request(method, path, body=body_data, headers=headers)
    else:
        client.request(method, path, headers=headers)
    response = client.getresponse()
    data = response.read().decode("utf-8")
    return response.status, json.loads(data) if data else {}


def demo_fileserver():
    """Run a comprehensive demo of the FileServer."""
    # Create a temporary directory for the demo
    temp_dir = tempfile.mkdtemp(prefix="fileserver_demo_")
    print(f"🚀 FileServer Demo")
    print(f"=" * 60)
    print(f"Demo directory: {temp_dir}\n")

    try:
        # Start server in background thread
        server = FileServer(root_dir=temp_dir, host="localhost", port=9999)
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        time.sleep(1)  # Give server time to start

        print("✓ Server started on http://localhost:9999\n")

        # Create HTTP client
        client = HTTPConnection("localhost", 9999)

        # 1. Health Check
        print("1. Testing Health Check Endpoint")
        print("-" * 60)
        status, data = make_request(client, "GET", "/health")
        print(f"   GET /health -> {status}")
        print(f"   Response: {json.dumps(data, indent=2)}")
        assert status == 200 and data["status"] == "ok"
        print("   ✓ Health check passed\n")

        # 2. Write Files
        print("2. Testing Write Operations")
        print("-" * 60)
        files_to_create = [
            ("hello.txt", "Hello, World!"),
            ("nested/deep/file.txt", "Nested content"),
            ("python.py", "print('Hello from Python')"),
            ("data.json", '{"key": "value", "number": 42}'),
        ]

        for file_path, content in files_to_create:
            status, data = make_request(client, "POST", "/api/write", {"file_path": file_path, "content": content})
            print(f"   POST /api/write (path={file_path}) -> {status}")
            assert status == 200 and data["error"] is None
            print(f"   ✓ Created: {file_path}")

        print(f"   ✓ All {len(files_to_create)} files created\n")

        # 3. Read Files
        print("3. Testing Read Operations")
        print("-" * 60)
        status, data = make_request(client, "GET", "/api/read?file_path=hello.txt")
        print(f"   GET /api/read?file_path=hello.txt -> {status}")
        print(f"   Content preview: {data['content'][:50]}...")
        assert "Hello, World!" in data["content"]
        print("   ✓ File read successfully\n")

        # 4. Edit Files
        print("4. Testing Edit Operations")
        print("-" * 60)
        status, data = make_request(
            client,
            "POST",
            "/api/edit",
            {"file_path": "hello.txt", "old_string": "World", "new_string": "FileServer"},
        )
        print(f"   POST /api/edit (hello.txt: World -> FileServer) -> {status}")
        print(f"   Occurrences replaced: {data['occurrences']}")
        assert data["occurrences"] == 1
        print("   ✓ File edited successfully")

        # Verify the edit
        status, data = make_request(client, "GET", "/api/read?file_path=hello.txt")
        assert "Hello, FileServer!" in data["content"]
        print("   ✓ Edit verified\n")

        # 5. List Directory
        print("5. Testing List Operations")
        print("-" * 60)
        status, data = make_request(client, "GET", f"/api/ls?path={temp_dir}")
        print(f"   GET /api/ls -> {status}")
        print(f"   Files found: {len(data['files'])}")
        for file_info in data["files"][:5]:  # Show first 5
            file_type = "DIR " if file_info["is_dir"] else "FILE"
            print(f"     [{file_type}] {Path(file_info['path']).name}")
        print("   ✓ Directory listed successfully\n")

        # 6. Grep Search
        print("6. Testing Grep (Search) Operations")
        print("-" * 60)
        status, data = make_request(client, "GET", f"/api/grep?pattern=Hello&path={temp_dir}")
        print(f"   GET /api/grep?pattern=Hello -> {status}")
        print(f"   Matches found: {len(data['matches'])}")
        for match in data["matches"]:
            filename = Path(match["path"]).name
            print(f"     {filename}:{match['line']} - {match['text'][:40]}...")
        assert len(data["matches"]) >= 1
        print("   ✓ Grep search successful\n")

        # 7. Glob Pattern Matching
        print("7. Testing Glob Pattern Matching")
        print("-" * 60)
        status, data = make_request(client, "GET", f"/api/glob?pattern=*.txt&path={temp_dir}")
        print(f"   GET /api/glob?pattern=*.txt -> {status}")
        print(f"   Files matching *.txt: {len(data['files'])}")
        for file_info in data["files"]:
            print(f"     {Path(file_info['path']).name} ({file_info['size']} bytes)")
        assert len(data["files"]) >= 2
        print("   ✓ Glob matching successful\n")

        # 8. Unicode Support
        print("8. Testing Unicode Support")
        print("-" * 60)
        unicode_content = "Hello 世界 🌍 Привет مرحبا"
        status, data = make_request(client, "POST", "/api/write", {"file_path": "unicode.txt", "content": unicode_content})
        print(f"   POST /api/write (unicode.txt) -> {status}")
        assert status == 200

        status, data = make_request(client, "GET", "/api/read?file_path=unicode.txt")
        print(f"   GET /api/read (unicode.txt) -> {status}")
        assert "世界" in data["content"] and "🌍" in data["content"]
        print(f"   Content: {unicode_content}")
        print("   ✓ Unicode handling successful\n")

        # 9. Error Handling
        print("9. Testing Error Handling")
        print("-" * 60)

        # Try to read nonexistent file
        status, data = make_request(client, "GET", "/api/read?file_path=nonexistent.txt")
        print(f"   GET /api/read (nonexistent.txt) -> {status}")
        assert "not found" in data["content"]
        print("   ✓ Nonexistent file error handled")

        # Try to write to existing file
        status, data = make_request(client, "POST", "/api/write", {"file_path": "hello.txt", "content": "new"})
        print(f"   POST /api/write (existing file) -> {status}")
        assert status == 400 and "already exists" in data["error"]
        print("   ✓ Duplicate file error handled")

        # Try invalid regex
        status, data = make_request(client, "GET", f"/api/grep?pattern=[invalid&path={temp_dir}")
        print(f"   GET /api/grep (invalid regex) -> {status}")
        assert status == 400
        print("   ✓ Invalid regex error handled\n")

        # Summary
        print("=" * 60)
        print("✅ All tests passed successfully!")
        print(f"Total files created: {len(files_to_create) + 1}")
        print(f"All BackendProtocol operations verified")
        print("=" * 60)

        # Stop server
        server.stop()

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            print(f"\n🧹 Cleaned up demo directory: {temp_dir}")
        except Exception:
            pass


if __name__ == "__main__":
    demo_fileserver()
