"""Comprehensive test suite for FileServer HTTP API.

Tests all BackendProtocol operations exposed via HTTP endpoints.
"""

import json
import shutil
import tempfile
import threading
import time
from http.client import HTTPConnection
from pathlib import Path

import pytest

from fileserver.server import FileServer


class TestFileServer:
    """Test suite for FileServer HTTP API."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def server(self, temp_dir):
        """Start a file server in a background thread."""
        server_instance = FileServer(root_dir=str(temp_dir), host="localhost", port=8888)
        thread = threading.Thread(target=server_instance.start, daemon=True)
        thread.start()
        time.sleep(0.5)  # Give server time to start
        yield server_instance
        server_instance.stop()

    @pytest.fixture
    def client(self):
        """Create HTTP client for testing."""
        return HTTPConnection("localhost", 8888)

    def _make_request(self, client, method, path, body=None):
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

    def test_health_endpoint(self, server, client):
        """Test health check endpoint."""
        status, data = self._make_request(client, "GET", "/health")
        assert status == 200
        assert data["status"] == "ok"

    def test_write_new_file(self, server, client, temp_dir):
        """Test creating a new file via POST /api/write."""
        status, data = self._make_request(client, "POST", "/api/write", {"file_path": "test.txt", "content": "Hello, World!"})
        assert status == 200
        assert data["error"] is None
        assert data["path"] == "test.txt"

        # Verify file was created
        file_path = temp_dir / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Hello, World!"

    def test_write_existing_file_fails(self, server, client, temp_dir):
        """Test that writing to an existing file returns an error."""
        # Create a file first
        (temp_dir / "existing.txt").write_text("Existing content")

        status, data = self._make_request(client, "POST", "/api/write", {"file_path": "existing.txt", "content": "New content"})
        assert status == 400
        assert "already exists" in data["error"]

    def test_write_nested_directory(self, server, client, temp_dir):
        """Test creating a file in a nested directory structure."""
        status, data = self._make_request(client, "POST", "/api/write", {"file_path": "a/b/c/test.txt", "content": "Nested file"})
        assert status == 200
        assert data["error"] is None

        # Verify nested file was created
        file_path = temp_dir / "a" / "b" / "c" / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Nested file"

    def test_read_file(self, server, client, temp_dir):
        """Test reading a file via GET /api/read."""
        # Create a test file
        test_file = temp_dir / "read_test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        status, data = self._make_request(client, "GET", "/api/read?file_path=read_test.txt")
        assert status == 200
        content = data["content"]
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content
        assert "1 |" in content  # Check line numbering

    def test_read_file_with_offset_and_limit(self, server, client, temp_dir):
        """Test reading file with offset and limit parameters."""
        # Create a test file with many lines
        test_file = temp_dir / "offset_test.txt"
        lines = [f"Line {i}" for i in range(1, 101)]
        test_file.write_text("\n".join(lines))

        # Read with offset and limit
        status, data = self._make_request(client, "GET", "/api/read?file_path=offset_test.txt&offset=10&limit=5")
        assert status == 200
        content = data["content"]
        assert "Line 11" in content  # Line at offset 10 (0-indexed)
        assert "Line 15" in content
        assert "Line 16" not in content  # Beyond limit

    def test_read_nonexistent_file(self, server, client):
        """Test reading a file that doesn't exist."""
        status, data = self._make_request(client, "GET", "/api/read?file_path=nonexistent.txt")
        assert status == 200
        assert "not found" in data["content"]

    def test_edit_file(self, server, client, temp_dir):
        """Test editing a file via POST /api/edit."""
        # Create a test file
        test_file = temp_dir / "edit_test.txt"
        test_file.write_text("Hello World\nHello Universe\n")

        # Edit the file
        status, data = self._make_request(
            client,
            "POST",
            "/api/edit",
            {"file_path": "edit_test.txt", "old_string": "World", "new_string": "Python"},
        )
        assert status == 200
        assert data["error"] is None
        assert data["occurrences"] == 1

        # Verify edit
        assert test_file.read_text() == "Hello Python\nHello Universe\n"

    def test_edit_file_replace_all(self, server, client, temp_dir):
        """Test editing a file with replace_all=True."""
        # Create a test file with multiple occurrences
        test_file = temp_dir / "replace_all_test.txt"
        test_file.write_text("foo bar foo baz foo")

        # Edit with replace_all
        status, data = self._make_request(
            client,
            "POST",
            "/api/edit",
            {"file_path": "replace_all_test.txt", "old_string": "foo", "new_string": "qux", "replace_all": True},
        )
        assert status == 200
        assert data["occurrences"] == 3

        # Verify all occurrences replaced
        assert test_file.read_text() == "qux bar qux baz qux"

    def test_edit_nonexistent_file(self, server, client):
        """Test editing a file that doesn't exist."""
        status, data = self._make_request(
            client,
            "POST",
            "/api/edit",
            {"file_path": "nonexistent.txt", "old_string": "old", "new_string": "new"},
        )
        assert status == 400
        assert "not found" in data["error"]

    def test_edit_string_not_found(self, server, client, temp_dir):
        """Test editing with a string that doesn't exist in the file."""
        test_file = temp_dir / "no_match.txt"
        test_file.write_text("Some content")

        status, data = self._make_request(
            client,
            "POST",
            "/api/edit",
            {"file_path": "no_match.txt", "old_string": "nonexistent", "new_string": "new"},
        )
        assert status == 400
        assert "not found" in data["error"]

    def test_ls_directory(self, server, client, temp_dir):
        """Test listing directory contents via GET /api/ls."""
        # Create test files and directories
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file3.txt").write_text("content3")

        status, data = self._make_request(client, "GET", f"/api/ls?path={temp_dir}")
        assert status == 200
        files = data["files"]

        # Check that direct children are listed
        paths = [f["path"] for f in files]
        assert any("file1.txt" in p for p in paths)
        assert any("file2.txt" in p for p in paths)
        assert any("subdir" in p for p in paths)

        # Check metadata
        file1_info = next(f for f in files if "file1.txt" in f["path"])
        assert file1_info["is_dir"] is False
        assert file1_info["size"] > 0
        assert "modified_at" in file1_info

        subdir_info = next(f for f in files if "subdir" in f["path"])
        assert subdir_info["is_dir"] is True
        assert subdir_info["path"].endswith("/")

    def test_ls_nonexistent_directory(self, server, client):
        """Test listing a directory that doesn't exist."""
        status, data = self._make_request(client, "GET", "/api/ls?path=/nonexistent")
        assert status == 200
        assert data["files"] == []

    def test_grep_pattern_search(self, server, client, temp_dir):
        """Test searching for patterns via GET /api/grep."""
        # Create test files
        (temp_dir / "file1.txt").write_text("Hello World\nHello Python\n")
        (temp_dir / "file2.txt").write_text("Goodbye World\n")
        (temp_dir / "file3.py").write_text("print('Hello')\n")

        status, data = self._make_request(client, "GET", f"/api/grep?pattern=Hello&path={temp_dir}")
        assert status == 200
        matches = data["matches"]

        assert len(matches) >= 2
        # Check structure
        for match in matches:
            assert "path" in match
            assert "line" in match
            assert "text" in match
            assert "Hello" in match["text"]

    def test_grep_with_glob_filter(self, server, client, temp_dir):
        """Test grep with glob pattern to filter files."""
        # Create test files
        (temp_dir / "file1.txt").write_text("pattern match\n")
        (temp_dir / "file2.py").write_text("pattern match\n")

        status, data = self._make_request(client, "GET", f"/api/grep?pattern=pattern&path={temp_dir}&glob=*.txt")
        assert status == 200
        matches = data["matches"]

        # Should only match .txt files
        for match in matches:
            assert match["path"].endswith(".txt")

    def test_grep_invalid_regex(self, server, client, temp_dir):
        """Test grep with invalid regex pattern."""
        status, data = self._make_request(client, "GET", f"/api/grep?pattern=[invalid&path={temp_dir}")
        assert status == 400
        assert "Invalid regex" in data["error"]

    def test_glob_pattern_matching(self, server, client, temp_dir):
        """Test glob pattern matching via GET /api/glob."""
        # Create test files
        (temp_dir / "test1.txt").write_text("content")
        (temp_dir / "test2.txt").write_text("content")
        (temp_dir / "test.py").write_text("content")
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "test3.txt").write_text("content")

        status, data = self._make_request(client, "GET", f"/api/glob?pattern=*.txt&path={temp_dir}")
        assert status == 200
        files = data["files"]

        # Should match all .txt files recursively
        paths = [f["path"] for f in files]
        assert len(paths) >= 3
        assert all(p.endswith(".txt") for p in paths)

    def test_glob_recursive_pattern(self, server, client, temp_dir):
        """Test recursive glob pattern matching."""
        # Create nested structure
        (temp_dir / "root.md").write_text("content")
        subdir1 = temp_dir / "sub1"
        subdir1.mkdir()
        (subdir1 / "file1.md").write_text("content")
        subdir2 = subdir1 / "sub2"
        subdir2.mkdir()
        (subdir2 / "file2.md").write_text("content")

        status, data = self._make_request(client, "GET", f"/api/glob?pattern=*.md&path={temp_dir}")
        assert status == 200
        files = data["files"]

        # Should match all .md files in all subdirectories
        paths = [f["path"] for f in files]
        assert len(paths) >= 3

    def test_glob_nonexistent_directory(self, server, client):
        """Test glob on nonexistent directory."""
        status, data = self._make_request(client, "GET", "/api/glob?pattern=*.txt&path=/nonexistent")
        assert status == 200
        assert data["files"] == []

    def test_write_empty_content(self, server, client, temp_dir):
        """Test writing an empty file."""
        status, data = self._make_request(client, "POST", "/api/write", {"file_path": "empty.txt", "content": ""})
        assert status == 200
        assert data["error"] is None

        file_path = temp_dir / "empty.txt"
        assert file_path.exists()
        assert file_path.read_text() == ""

    def test_read_empty_file(self, server, client, temp_dir):
        """Test reading an empty file."""
        (temp_dir / "empty.txt").write_text("")

        status, data = self._make_request(client, "GET", "/api/read?file_path=empty.txt")
        assert status == 200
        assert "empty" in data["content"].lower()

    def test_unicode_content(self, server, client, temp_dir):
        """Test handling Unicode content."""
        unicode_content = "Hello 世界 🌍 Привет"

        status, data = self._make_request(client, "POST", "/api/write", {"file_path": "unicode.txt", "content": unicode_content})
        assert status == 200

        # Read back
        status, data = self._make_request(client, "GET", "/api/read?file_path=unicode.txt")
        assert status == 200
        assert "世界" in data["content"]
        assert "🌍" in data["content"]
        assert "Привет" in data["content"]

    def test_concurrent_operations(self, server, client, temp_dir):
        """Test multiple concurrent operations."""
        # Write multiple files
        for i in range(5):
            status, data = self._make_request(client, "POST", "/api/write", {"file_path": f"file{i}.txt", "content": f"Content {i}"})
            assert status == 200

        # Read them back
        for i in range(5):
            status, data = self._make_request(client, "GET", f"/api/read?file_path=file{i}.txt")
            assert status == 200
            assert f"Content {i}" in data["content"]

    def test_error_handling_missing_parameters(self, server, client):
        """Test error handling for missing required parameters."""
        # Missing file_path for read
        status, data = self._make_request(client, "GET", "/api/read")
        assert status == 400
        assert "required" in data["error"]

        # Missing pattern for grep
        status, data = self._make_request(client, "GET", "/api/grep")
        assert status == 400
        assert "required" in data["error"]

        # Missing pattern for glob
        status, data = self._make_request(client, "GET", "/api/glob")
        assert status == 400
        assert "required" in data["error"]

    def test_invalid_json_body(self, server, client):
        """Test handling of invalid JSON in request body."""
        client.request(
            "POST",
            "/api/write",
            body=b"invalid json{",
            headers={"Content-Type": "application/json"},
        )
        response = client.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        assert response.status == 400
        assert "Invalid JSON" in data["error"]

    def test_not_found_endpoint(self, server, client):
        """Test accessing a nonexistent endpoint."""
        status, data = self._make_request(client, "GET", "/api/nonexistent")
        assert status == 404
        assert "Not found" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
