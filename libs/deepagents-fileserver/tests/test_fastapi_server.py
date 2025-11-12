"""Comprehensive test suite for FastAPI FileServer with security features.

Tests all BackendProtocol operations exposed via FastAPI endpoints.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fileserver.fastapi_server import SecureFileServer


class TestFastAPIFileServer:
    """Test suite for FastAPI FileServer."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def server_no_auth(self, temp_dir):
        """Create a file server without authentication."""
        return SecureFileServer(root_dir=str(temp_dir), enable_auth=False)

    @pytest.fixture
    def server_with_auth(self, temp_dir):
        """Create a file server with authentication."""
        return SecureFileServer(root_dir=str(temp_dir), api_key="test-api-key-12345", enable_auth=True)

    @pytest.fixture
    def client_no_auth(self, server_no_auth):
        """Create test client without authentication."""
        return TestClient(server_no_auth.app)

    @pytest.fixture
    def client_with_auth(self, server_with_auth):
        """Create test client with authentication."""
        client = TestClient(server_with_auth.app)
        client.headers = {"X-API-Key": "test-api-key-12345"}
        return client

    def test_health_endpoint(self, client_no_auth):
        """Test health check endpoint."""
        response = client_no_auth.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_endpoint_no_auth_required(self, server_with_auth):
        """Test health check endpoint doesn't require authentication."""
        client = TestClient(server_with_auth.app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_authentication_required(self, server_with_auth, temp_dir):
        """Test that authentication is required for protected endpoints."""
        client = TestClient(server_with_auth.app)

        # Try without API key
        response = client.get("/api/ls")
        assert response.status_code == 401
        assert "Invalid or missing API key" in response.json()["detail"]

    def test_authentication_invalid_key(self, server_with_auth):
        """Test that invalid API key is rejected."""
        client = TestClient(server_with_auth.app)
        response = client.get("/api/ls", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 401

    def test_authentication_valid_key(self, client_with_auth):
        """Test that valid API key is accepted."""
        response = client_with_auth.get("/api/ls")
        assert response.status_code == 200

    def test_write_new_file(self, client_no_auth, temp_dir):
        """Test creating a new file via POST /api/write."""
        response = client_no_auth.post("/api/write", json={"file_path": "test.txt", "content": "Hello, World!"})
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["path"] == "test.txt"

        # Verify file was created
        file_path = temp_dir / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Hello, World!"

    def test_write_existing_file_fails(self, client_no_auth, temp_dir):
        """Test that writing to an existing file returns an error."""
        (temp_dir / "existing.txt").write_text("Existing content")

        response = client_no_auth.post("/api/write", json={"file_path": "existing.txt", "content": "New content"})
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_write_nested_directory(self, client_no_auth, temp_dir):
        """Test creating a file in a nested directory structure."""
        response = client_no_auth.post("/api/write", json={"file_path": "a/b/c/test.txt", "content": "Nested file"})
        assert response.status_code == 200
        assert response.json()["error"] is None

        # Verify nested file was created
        file_path = temp_dir / "a" / "b" / "c" / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Nested file"

    def test_path_traversal_prevention(self, client_no_auth, temp_dir):
        """Test that path traversal attempts are blocked."""
        response = client_no_auth.post("/api/write", json={"file_path": "../../../etc/passwd", "content": "malicious"})
        assert response.status_code == 403
        assert "Path traversal detected" in response.json()["detail"]

    def test_path_traversal_read(self, client_no_auth):
        """Test that path traversal attempts are blocked in read operations."""
        response = client_no_auth.get("/api/read?file_path=../../etc/passwd")
        assert response.status_code == 403
        assert "Path traversal detected" in response.json()["detail"]

    def test_read_file(self, client_no_auth, temp_dir):
        """Test reading a file via GET /api/read."""
        test_file = temp_dir / "read_test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        response = client_no_auth.get("/api/read?file_path=read_test.txt")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content
        assert "1 |" in content

    def test_read_file_with_offset_and_limit(self, client_no_auth, temp_dir):
        """Test reading file with offset and limit parameters."""
        test_file = temp_dir / "offset_test.txt"
        lines = [f"Line {i}" for i in range(1, 101)]
        test_file.write_text("\n".join(lines))

        response = client_no_auth.get("/api/read?file_path=offset_test.txt&offset=10&limit=5")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "Line 11" in content
        assert "Line 15" in content
        assert "Line 16" not in content

    def test_read_nonexistent_file(self, client_no_auth):
        """Test reading a file that doesn't exist."""
        response = client_no_auth.get("/api/read?file_path=nonexistent.txt")
        assert response.status_code == 200
        assert "not found" in response.json()["content"]

    def test_edit_file(self, client_no_auth, temp_dir):
        """Test editing a file via POST /api/edit."""
        test_file = temp_dir / "edit_test.txt"
        test_file.write_text("Hello World\nHello Universe\n")

        response = client_no_auth.post(
            "/api/edit",
            json={
                "file_path": "edit_test.txt",
                "old_string": "World",
                "new_string": "Python",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["occurrences"] == 1

        # Verify edit
        assert test_file.read_text() == "Hello Python\nHello Universe\n"

    def test_edit_file_replace_all(self, client_no_auth, temp_dir):
        """Test editing a file with replace_all=True."""
        test_file = temp_dir / "replace_all_test.txt"
        test_file.write_text("foo bar foo baz foo")

        response = client_no_auth.post(
            "/api/edit",
            json={
                "file_path": "replace_all_test.txt",
                "old_string": "foo",
                "new_string": "qux",
                "replace_all": True,
            },
        )
        assert response.status_code == 200
        assert response.json()["occurrences"] == 3

        # Verify all occurrences replaced
        assert test_file.read_text() == "qux bar qux baz qux"

    def test_edit_nonexistent_file(self, client_no_auth):
        """Test editing a file that doesn't exist."""
        response = client_no_auth.post(
            "/api/edit",
            json={
                "file_path": "nonexistent.txt",
                "old_string": "old",
                "new_string": "new",
            },
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_edit_string_not_found(self, client_no_auth, temp_dir):
        """Test editing with a string that doesn't exist in the file."""
        test_file = temp_dir / "no_match.txt"
        test_file.write_text("Some content")

        response = client_no_auth.post(
            "/api/edit",
            json={
                "file_path": "no_match.txt",
                "old_string": "nonexistent",
                "new_string": "new",
            },
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_ls_directory(self, client_no_auth, temp_dir):
        """Test listing directory contents via GET /api/ls."""
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file3.txt").write_text("content3")

        response = client_no_auth.get(f"/api/ls?path={temp_dir}")
        assert response.status_code == 200
        files = response.json()["files"]

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

    def test_ls_nonexistent_directory(self, client_no_auth):
        """Test listing a directory that doesn't exist."""
        response = client_no_auth.get("/api/ls?path=/nonexistent")
        assert response.status_code == 200
        assert response.json()["files"] == []

    def test_grep_pattern_search(self, client_no_auth, temp_dir):
        """Test searching for patterns via GET /api/grep."""
        (temp_dir / "file1.txt").write_text("Hello World\nHello Python\n")
        (temp_dir / "file2.txt").write_text("Goodbye World\n")
        (temp_dir / "file3.py").write_text("print('Hello')\n")

        response = client_no_auth.get(f"/api/grep?pattern=Hello&path={temp_dir}")
        assert response.status_code == 200
        matches = response.json()["matches"]

        assert len(matches) >= 2
        for match in matches:
            assert "path" in match
            assert "line" in match
            assert "text" in match
            assert "Hello" in match["text"]

    def test_grep_with_glob_filter(self, client_no_auth, temp_dir):
        """Test grep with glob pattern to filter files."""
        (temp_dir / "file1.txt").write_text("pattern match\n")
        (temp_dir / "file2.py").write_text("pattern match\n")

        response = client_no_auth.get(f"/api/grep?pattern=pattern&path={temp_dir}&glob=*.txt")
        assert response.status_code == 200
        matches = response.json()["matches"]

        # Should only match .txt files
        for match in matches:
            assert match["path"].endswith(".txt")

    def test_grep_invalid_regex(self, client_no_auth, temp_dir):
        """Test grep with invalid regex pattern."""
        response = client_no_auth.get(f"/api/grep?pattern=[invalid&path={temp_dir}")
        assert response.status_code == 400
        assert "Invalid regex" in response.json()["detail"]

    def test_glob_pattern_matching(self, client_no_auth, temp_dir):
        """Test glob pattern matching via GET /api/glob."""
        (temp_dir / "test1.txt").write_text("content")
        (temp_dir / "test2.txt").write_text("content")
        (temp_dir / "test.py").write_text("content")
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "test3.txt").write_text("content")

        response = client_no_auth.get(f"/api/glob?pattern=*.txt&path={temp_dir}")
        assert response.status_code == 200
        files = response.json()["files"]

        # Should match all .txt files recursively
        paths = [f["path"] for f in files]
        assert len(paths) >= 3
        assert all(p.endswith(".txt") for p in paths)

    def test_glob_recursive_pattern(self, client_no_auth, temp_dir):
        """Test recursive glob pattern matching."""
        (temp_dir / "root.md").write_text("content")
        subdir1 = temp_dir / "sub1"
        subdir1.mkdir()
        (subdir1 / "file1.md").write_text("content")
        subdir2 = subdir1 / "sub2"
        subdir2.mkdir()
        (subdir2 / "file2.md").write_text("content")

        response = client_no_auth.get(f"/api/glob?pattern=*.md&path={temp_dir}")
        assert response.status_code == 200
        files = response.json()["files"]

        # Should match all .md files in all subdirectories
        paths = [f["path"] for f in files]
        assert len(paths) >= 3

    def test_glob_nonexistent_directory(self, client_no_auth):
        """Test glob on nonexistent directory."""
        response = client_no_auth.get("/api/glob?pattern=*.txt&path=/nonexistent")
        assert response.status_code == 200
        assert response.json()["files"] == []

    def test_write_empty_content(self, client_no_auth, temp_dir):
        """Test writing an empty file."""
        response = client_no_auth.post("/api/write", json={"file_path": "empty.txt", "content": ""})
        assert response.status_code == 200
        assert response.json()["error"] is None

        file_path = temp_dir / "empty.txt"
        assert file_path.exists()
        assert file_path.read_text() == ""

    def test_read_empty_file(self, client_no_auth, temp_dir):
        """Test reading an empty file."""
        (temp_dir / "empty.txt").write_text("")

        response = client_no_auth.get("/api/read?file_path=empty.txt")
        assert response.status_code == 200
        assert "empty" in response.json()["content"].lower()

    def test_unicode_content(self, client_no_auth, temp_dir):
        """Test handling Unicode content."""
        unicode_content = "Hello 世界 🌍 Привет"

        response = client_no_auth.post("/api/write", json={"file_path": "unicode.txt", "content": unicode_content})
        assert response.status_code == 200

        # Read back
        response = client_no_auth.get("/api/read?file_path=unicode.txt")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "世界" in content
        assert "🌍" in content
        assert "Привет" in content

    def test_concurrent_operations(self, client_no_auth, temp_dir):
        """Test multiple concurrent operations."""
        # Write multiple files
        for i in range(5):
            response = client_no_auth.post("/api/write", json={"file_path": f"file{i}.txt", "content": f"Content {i}"})
            assert response.status_code == 200

        # Read them back
        for i in range(5):
            response = client_no_auth.get(f"/api/read?file_path=file{i}.txt")
            assert response.status_code == 200
            assert f"Content {i}" in response.json()["content"]

    def test_openapi_docs(self, client_no_auth):
        """Test that OpenAPI documentation is available."""
        response = client_no_auth.get("/docs")
        assert response.status_code == 200

        response = client_no_auth.get("/redoc")
        assert response.status_code == 200

        response = client_no_auth.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_auto_generated_api_key(self, temp_dir):
        """Test that API key is auto-generated when not provided."""
        server = SecureFileServer(root_dir=str(temp_dir), enable_auth=True)
        assert server.api_key is not None
        assert len(server.api_key) > 20

    def test_custom_api_key(self, temp_dir):
        """Test using a custom API key."""
        custom_key = "my-custom-key-123"
        server = SecureFileServer(root_dir=str(temp_dir), api_key=custom_key, enable_auth=True)
        assert server.api_key == custom_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
