"""Integration test for FileServer - verifies server works in production scenario."""

import subprocess
import sys
import tempfile
import time
from http.client import HTTPConnection
from pathlib import Path


def test_server_integration():
    """Integration test that starts a real server and tests it."""
    print("🧪 FileServer Integration Test")
    print("=" * 60)

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="fileserver_integration_")
    print(f"Test directory: {temp_dir}")

    # Start server as subprocess
    print("Starting FileServer on port 8765...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "fileserver.server", temp_dir, "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to start
    time.sleep(2)

    try:
        # Test connection
        client = HTTPConnection("localhost", 8765, timeout=5)

        # Test 1: Health check
        print("\n1. Testing health endpoint...")
        client.request("GET", "/health")
        response = client.getresponse()
        assert response.status == 200, f"Health check failed: {response.status}"
        print("   ✓ Health check passed")

        # Test 2: Write a file
        print("\n2. Testing write operation...")
        import json

        body = json.dumps({"file_path": "integration_test.txt", "content": "Integration test content"})
        client.request("POST", "/api/write", body=body.encode(), headers={"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200, f"Write failed: {response.status}"
        print("   ✓ Write operation passed")

        # Verify file exists
        test_file = Path(temp_dir) / "integration_test.txt"
        assert test_file.exists(), "File was not created"
        print("   ✓ File verified on disk")

        # Test 3: Read the file
        print("\n3. Testing read operation...")
        client.request("GET", "/api/read?file_path=integration_test.txt")
        response = client.getresponse()
        data = response.read().decode("utf-8")
        assert response.status == 200, f"Read failed: {response.status}"
        assert "Integration test content" in data, "Content not found"
        print("   ✓ Read operation passed")

        # Test 4: List directory
        print("\n4. Testing ls operation...")
        client.request("GET", f"/api/ls?path={temp_dir}")
        response = client.getresponse()
        data = response.read().decode("utf-8")
        assert response.status == 200, f"Ls failed: {response.status}"
        assert "integration_test.txt" in data, "File not listed"
        print("   ✓ Ls operation passed")

        # Test 5: Grep search
        print("\n5. Testing grep operation...")
        client.request("GET", f"/api/grep?pattern=Integration&path={temp_dir}")
        response = client.getresponse()
        data = response.read().decode("utf-8")
        assert response.status == 200, f"Grep failed: {response.status}"
        assert "Integration" in data, "Pattern not found"
        print("   ✓ Grep operation passed")

        print("\n" + "=" * 60)
        print("✅ All integration tests passed!")
        print("=" * 60)

        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    finally:
        # Cleanup
        print("\nCleaning up...")
        server_process.terminate()
        server_process.wait(timeout=5)
        print("Server stopped")

        # Remove temp directory
        import shutil

        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up: {temp_dir}")
        except Exception:
            pass


if __name__ == "__main__":
    success = test_server_integration()
    sys.exit(0 if success else 1)
