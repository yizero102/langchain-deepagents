"""Comprehensive test suite for FastAPI FileServer with security features."""

import shutil
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fileserver.fastapi_server import FastAPIFileServer


class TestFastAPIFileServer:
    """Test suite for FastAPI FileServer."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def server_with_auth(self, temp_dir):
        """Create a server with authentication enabled."""
        server = FastAPIFileServer(
            root_dir=str(temp_dir),
            api_key="test-api-key-12345",
            enable_auth=True,
            enable_rate_limit=False,
        )
        return server

    @pytest.fixture
    def server_without_auth(self, temp_dir):
        """Create a server without authentication."""
        server = FastAPIFileServer(
            root_dir=str(temp_dir),
            enable_auth=False,
            enable_rate_limit=False,
        )
        return server

    @pytest.fixture
    def server_with_rate_limit(self, temp_dir):
        """Create a server with rate limiting enabled."""
        server = FastAPIFileServer(
            root_dir=str(temp_dir),
            enable_auth=False,
            enable_rate_limit=True,
            max_requests=5,
            window_seconds=60,
        )
        return server

    @pytest.fixture
    def client_with_auth(self, server_with_auth):
        """Create a test client with authentication."""
        return TestClient(server_with_auth.app)

    @pytest.fixture
    def client_without_auth(self, server_without_auth):
        """Create a test client without authentication."""
        return TestClient(server_without_auth.app)

    @pytest.fixture
    def client_with_rate_limit(self, server_with_rate_limit):
        """Create a test client with rate limiting."""
        return TestClient(server_with_rate_limit.app)

    # ===== Health Check Tests =====

    def test_health_check(self, client_without_auth):
        """Test health check endpoint."""
        response = client_without_auth.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "uptime" in data
        assert data["version"] == "2.0.0"

    # ===== Authentication Tests =====

    def test_auth_required_missing_header(self, client_with_auth):
        """Test that requests without API key are rejected."""
        response = client_with_auth.get("/api/ls")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_auth_required_invalid_key(self, client_with_auth):
        """Test that requests with invalid API key are rejected."""
        response = client_with_auth.get("/api/ls", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]

    def test_auth_required_valid_key(self, client_with_auth, temp_dir):
        """Test that requests with valid API key are accepted."""
        (temp_dir / "test.txt").write_text("content")
        response = client_with_auth.get("/api/ls?path=.", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200
        data = response.json()
        assert "files" in data

    def test_auth_disabled_allows_all(self, client_without_auth):
        """Test that server without auth allows all requests."""
        response = client_without_auth.get("/api/ls")
        assert response.status_code == 200

    # ===== Rate Limiting Tests =====

    def test_rate_limiting_enforced(self, client_with_rate_limit):
        """Test that rate limiting is enforced."""
        # Make 5 requests (the limit)
        for i in range(5):
            response = client_with_rate_limit.get("/api/ls")
            assert response.status_code == 200

        # 6th request should be rate limited
        response = client_with_rate_limit.get("/api/ls")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    # ===== Security Tests (Path Traversal) =====

    def test_path_traversal_blocked_write(self, client_without_auth):
        """Test that path traversal is blocked in write operations."""
        response = client_without_auth.post(
            "/api/write",
            json={"file_path": "../../../etc/passwd", "content": "malicious"},
        )
        assert response.status_code == 422  # Validation error

    def test_path_traversal_blocked_read(self, client_without_auth, temp_dir):
        """Test that path traversal is blocked in read operations."""
        # Create a file outside the root
        outside_file = temp_dir.parent / "outside.txt"
        outside_file.write_text("outside content")

        # Try to read it using path traversal
        response = client_without_auth.get("/api/read?file_path=../outside.txt")
        assert response.status_code == 200
        data = response.json()
        assert "Error" in data["content"]  # Should fail, not return content

    def test_absolute_path_blocked(self, client_without_auth):
        """Test that absolute paths are blocked."""
        response = client_without_auth.post(
            "/api/write",
            json={"file_path": "/etc/passwd", "content": "malicious"},
        )
        assert response.status_code == 422  # Validation error

    # ===== Write Operation Tests =====

    def test_write_new_file(self, client_without_auth, temp_dir):
        """Test creating a new file."""
        response = client_without_auth.post(
            "/api/write",
            json={"file_path": "test.txt", "content": "Hello, World!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["path"] == "test.txt"

        # Verify file was created
        file_path = temp_dir / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Hello, World!"

    def test_write_existing_file_fails(self, client_without_auth, temp_dir):
        """Test that writing to existing file returns error."""
        (temp_dir / "existing.txt").write_text("existing content")

        response = client_without_auth.post(
            "/api/write",
            json={"file_path": "existing.txt", "content": "new content"},
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_write_nested_directory(self, client_without_auth, temp_dir):
        """Test creating file in nested directory."""
        response = client_without_auth.post(
            "/api/write",
            json={"file_path": "a/b/c/test.txt", "content": "nested"},
        )
        assert response.status_code == 200

        file_path = temp_dir / "a" / "b" / "c" / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "nested"

    def test_write_empty_content(self, client_without_auth, temp_dir):
        """Test writing empty file."""
        response = client_without_auth.post(
            "/api/write",
            json={"file_path": "empty.txt", "content": ""},
        )
        assert response.status_code == 200

        file_path = temp_dir / "empty.txt"
        assert file_path.exists()
        assert file_path.read_text() == ""

    def test_write_unicode_content(self, client_without_auth, temp_dir):
        """Test writing Unicode content."""
        unicode_content = "Hello 世界 🌍 Привет"
        response = client_without_auth.post(
            "/api/write",
            json={"file_path": "unicode.txt", "content": unicode_content},
        )
        assert response.status_code == 200

        file_path = temp_dir / "unicode.txt"
        assert file_path.read_text() == unicode_content

    # ===== Read Operation Tests =====

    def test_read_file(self, client_without_auth, temp_dir):
        """Test reading a file."""
        test_file = temp_dir / "read_test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3")

        response = client_without_auth.get("/api/read?file_path=read_test.txt")
        assert response.status_code == 200
        data = response.json()
        content = data["content"]
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content
        assert "1 |" in content  # Line numbering

    def test_read_with_offset_and_limit(self, client_without_auth, temp_dir):
        """Test reading with offset and limit."""
        test_file = temp_dir / "offset_test.txt"
        lines = [f"Line {i}" for i in range(1, 21)]
        test_file.write_text("\n".join(lines))

        response = client_without_auth.get("/api/read?file_path=offset_test.txt&offset=5&limit=3")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "Line 6" in content
        assert "Line 7" in content
        assert "Line 8" in content
        assert "Line 9" not in content

    def test_read_nonexistent_file(self, client_without_auth):
        """Test reading nonexistent file."""
        response = client_without_auth.get("/api/read?file_path=nonexistent.txt")
        assert response.status_code == 200
        assert "not found" in response.json()["content"]

    # ===== Edit Operation Tests =====

    def test_edit_file(self, client_without_auth, temp_dir):
        """Test editing a file."""
        test_file = temp_dir / "edit_test.txt"
        test_file.write_text("Hello World\nHello Universe")

        response = client_without_auth.post(
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

        assert test_file.read_text() == "Hello Python\nHello Universe"

    def test_edit_replace_all(self, client_without_auth, temp_dir):
        """Test editing with replace_all=True."""
        test_file = temp_dir / "replace_all_test.txt"
        test_file.write_text("foo bar foo baz foo")

        response = client_without_auth.post(
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
        assert test_file.read_text() == "qux bar qux baz qux"

    def test_edit_nonexistent_file(self, client_without_auth):
        """Test editing nonexistent file."""
        response = client_without_auth.post(
            "/api/edit",
            json={
                "file_path": "nonexistent.txt",
                "old_string": "old",
                "new_string": "new",
            },
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_edit_string_not_found(self, client_without_auth, temp_dir):
        """Test editing with string that doesn't exist."""
        test_file = temp_dir / "no_match.txt"
        test_file.write_text("Some content")

        response = client_without_auth.post(
            "/api/edit",
            json={
                "file_path": "no_match.txt",
                "old_string": "nonexistent",
                "new_string": "new",
            },
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    # ===== List Directory Tests =====

    def test_ls_directory(self, client_without_auth, temp_dir):
        """Test listing directory."""
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "subdir").mkdir()

        response = client_without_auth.get("/api/ls?path=.")
        assert response.status_code == 200
        data = response.json()
        files = data["files"]

        paths = [f["path"] for f in files]
        assert any("file1.txt" in p for p in paths)
        assert any("file2.txt" in p for p in paths)
        assert any("subdir" in p for p in paths)

    def test_ls_nonexistent_directory(self, client_without_auth):
        """Test listing nonexistent directory."""
        response = client_without_auth.get("/api/ls?path=nonexistent")
        assert response.status_code == 200
        assert response.json()["files"] == []

    # ===== Grep Tests =====

    def test_grep_pattern_search(self, client_without_auth, temp_dir):
        """Test grep pattern search."""
        (temp_dir / "file1.txt").write_text("Hello World\nHello Python")
        (temp_dir / "file2.txt").write_text("Goodbye World")

        response = client_without_auth.get("/api/grep?pattern=Hello&path=.")
        assert response.status_code == 200
        matches = response.json()["matches"]

        assert len(matches) >= 2
        for match in matches:
            assert "path" in match
            assert "line" in match
            assert "text" in match
            assert "Hello" in match["text"]

    def test_grep_with_glob_filter(self, client_without_auth, temp_dir):
        """Test grep with glob filter."""
        (temp_dir / "file1.txt").write_text("pattern match")
        (temp_dir / "file2.py").write_text("pattern match")

        response = client_without_auth.get("/api/grep?pattern=pattern&path=.&glob=*.txt")
        assert response.status_code == 200
        matches = response.json()["matches"]

        for match in matches:
            assert match["path"].endswith(".txt")

    def test_grep_invalid_regex(self, client_without_auth):
        """Test grep with invalid regex."""
        response = client_without_auth.get("/api/grep?pattern=[invalid")
        assert response.status_code == 400
        assert "Invalid regex" in response.json()["detail"]

    # ===== Glob Tests =====

    def test_glob_pattern_matching(self, client_without_auth, temp_dir):
        """Test glob pattern matching."""
        (temp_dir / "test1.txt").write_text("content")
        (temp_dir / "test2.txt").write_text("content")
        (temp_dir / "test.py").write_text("content")
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "test3.txt").write_text("content")

        response = client_without_auth.get("/api/glob?pattern=*.txt&path=.")
        assert response.status_code == 200
        files = response.json()["files"]

        paths = [f["path"] for f in files]
        assert len(paths) >= 3
        assert all(p.endswith(".txt") for p in paths)

    def test_glob_recursive_pattern(self, client_without_auth, temp_dir):
        """Test recursive glob pattern."""
        (temp_dir / "root.md").write_text("content")
        subdir1 = temp_dir / "sub1"
        subdir1.mkdir()
        (subdir1 / "file1.md").write_text("content")
        subdir2 = subdir1 / "sub2"
        subdir2.mkdir()
        (subdir2 / "file2.md").write_text("content")

        response = client_without_auth.get("/api/glob?pattern=*.md&path=.")
        assert response.status_code == 200
        files = response.json()["files"]

        paths = [f["path"] for f in files]
        assert len(paths) >= 3

    # ===== Edge Cases and Error Handling =====

    def test_invalid_request_missing_required_params(self, client_without_auth):
        """Test error handling for missing required parameters."""
        # Missing file_path for read
        response = client_without_auth.get("/api/read")
        assert response.status_code == 422  # Validation error

        # Missing pattern for grep
        response = client_without_auth.get("/api/grep")
        assert response.status_code == 422

        # Missing pattern for glob
        response = client_without_auth.get("/api/glob")
        assert response.status_code == 422

    def test_concurrent_operations(self, client_without_auth, temp_dir):
        """Test multiple concurrent operations."""
        # Write multiple files
        for i in range(5):
            response = client_without_auth.post(
                "/api/write",
                json={"file_path": f"file{i}.txt", "content": f"Content {i}"},
            )
            assert response.status_code == 200

        # Read them back
        for i in range(5):
            response = client_without_auth.get(f"/api/read?file_path=file{i}.txt")
            assert response.status_code == 200
            assert f"Content {i}" in response.json()["content"]

    def test_large_file_handling(self, client_without_auth, temp_dir):
        """Test handling of large files."""
        # Create a large file
        large_content = "x" * 10000
        (temp_dir / "large.txt").write_text(large_content)

        # Should be able to read it
        response = client_without_auth.get("/api/read?file_path=large.txt&limit=100")
        assert response.status_code == 200

    def test_special_characters_in_content(self, client_without_auth, temp_dir):
        """Test handling special characters."""
        special_content = "Special chars: <>&\"'\n\t\r"
        response = client_without_auth.post(
            "/api/write",
            json={"file_path": "special.txt", "content": special_content},
        )
        assert response.status_code == 200

        # Read back
        response = client_without_auth.get("/api/read?file_path=special.txt")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "<>" in content
        assert "&" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
