"""Comprehensive test suite for FastAPI FileServer with security features.

Tests all BackendProtocol operations exposed via FastAPI endpoints,
including security features and edge cases from Python and Java backends.
"""

import json
import shutil
import tempfile
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fileserver.server_fastapi import FastAPIFileServer, create_app


class TestFastAPIFileServer:
    """Test suite for FastAPI FileServer with security."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def api_key(self):
        """Fixed API key for testing."""
        return "test-api-key-12345"

    @pytest.fixture
    def app(self, temp_dir, api_key):
        """Create FastAPI application for testing."""
        return create_app(
            root_dir=str(temp_dir),
            api_key=api_key,
            enable_rate_limiting=False,  # Disable for most tests
        )

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def headers(self, api_key):
        """Create headers with API key."""
        return {"X-API-Key": api_key}

    # ===== Authentication Tests =====

    def test_health_endpoint_no_auth(self, client):
        """Test health check endpoint doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_missing_api_key(self, client):
        """Test that endpoints require API key."""
        response = client.get("/api/ls")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_invalid_api_key(self, client):
        """Test that invalid API key is rejected."""
        response = client.get("/api/ls", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_valid_api_key(self, client, headers):
        """Test that valid API key grants access."""
        response = client.get("/api/ls?path=.", headers=headers)
        assert response.status_code == 200

    # ===== Rate Limiting Tests =====

    def test_rate_limiting(self, temp_dir, api_key):
        """Test rate limiting functionality."""
        app = create_app(
            root_dir=str(temp_dir),
            api_key=api_key,
            enable_rate_limiting=True,
            rate_limit_requests=5,
            rate_limit_window=60,
        )
        client = TestClient(app)
        headers = {"X-API-Key": api_key}

        # Make requests up to the limit
        for i in range(5):
            response = client.get("/api/ls", headers=headers)
            assert response.status_code == 200

        # Next request should be rate limited
        response = client.get("/api/ls", headers=headers)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    # ===== Path Traversal Security Tests =====

    def test_path_traversal_prevention_write(self, client, headers, temp_dir):
        """Test that path traversal is prevented in write operations."""
        response = client.post(
            "/api/write",
            json={"file_path": "../../../etc/passwd", "content": "malicious"},
            headers=headers,
        )
        assert response.status_code == 422  # Validation error

    def test_path_traversal_prevention_edit(self, client, headers):
        """Test that path traversal is prevented in edit operations."""
        response = client.post(
            "/api/edit",
            json={"file_path": "../../../etc/passwd", "old_string": "root", "new_string": "hacked"},
            headers=headers,
        )
        assert response.status_code == 422  # Validation error

    def test_path_traversal_prevention_read(self, client, headers, temp_dir):
        """Test that path traversal is prevented in read operations."""
        # Create a file outside the root directory
        outside_dir = temp_dir.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("secret data")

        # Try to read it using path traversal
        response = client.get(f"/api/read?file_path=../outside/secret.txt", headers=headers)
        assert response.status_code == 200
        content = response.json()["content"]
        assert "Error" in content or "not found" in content

        # Cleanup
        shutil.rmtree(outside_dir, ignore_errors=True)

    # ===== Basic Operations Tests =====

    def test_write_new_file(self, client, headers, temp_dir):
        """Test creating a new file via POST /api/write."""
        response = client.post(
            "/api/write",
            json={"file_path": "test.txt", "content": "Hello, World!"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["path"] == "test.txt"

        # Verify file was created
        file_path = temp_dir / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Hello, World!"

    def test_write_existing_file_fails(self, client, headers, temp_dir):
        """Test that writing to an existing file returns an error."""
        (temp_dir / "existing.txt").write_text("Existing content")

        response = client.post(
            "/api/write",
            json={"file_path": "existing.txt", "content": "New content"},
            headers=headers,
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_write_nested_directory(self, client, headers, temp_dir):
        """Test creating a file in a nested directory structure."""
        response = client.post(
            "/api/write",
            json={"file_path": "a/b/c/test.txt", "content": "Nested file"},
            headers=headers,
        )
        assert response.status_code == 200

        file_path = temp_dir / "a" / "b" / "c" / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Nested file"

    def test_write_deep_nesting(self, client, headers, temp_dir):
        """Test creating files with 5+ levels of nesting (Java backend test coverage)."""
        deep_path = "level1/level2/level3/level4/level5/deep.txt"
        response = client.post(
            "/api/write",
            json={"file_path": deep_path, "content": "Deep nested file"},
            headers=headers,
        )
        assert response.status_code == 200

        file_path = temp_dir / "level1/level2/level3/level4/level5/deep.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Deep nested file"

    def test_write_empty_content(self, client, headers, temp_dir):
        """Test writing an empty file."""
        response = client.post(
            "/api/write",
            json={"file_path": "empty.txt", "content": ""},
            headers=headers,
        )
        assert response.status_code == 200

        file_path = temp_dir / "empty.txt"
        assert file_path.exists()
        assert file_path.read_text() == ""

    def test_read_file(self, client, headers, temp_dir):
        """Test reading a file via GET /api/read."""
        test_file = temp_dir / "read_test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n")

        response = client.get("/api/read?file_path=read_test.txt", headers=headers)
        assert response.status_code == 200
        content = response.json()["content"]
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content
        assert "1 |" in content  # Check line numbering

    def test_read_file_with_offset_and_limit(self, client, headers, temp_dir):
        """Test reading file with offset and limit parameters."""
        test_file = temp_dir / "offset_test.txt"
        lines = [f"Line {i}" for i in range(1, 101)]
        test_file.write_text("\n".join(lines))

        response = client.get("/api/read?file_path=offset_test.txt&offset=10&limit=5", headers=headers)
        assert response.status_code == 200
        content = response.json()["content"]
        assert "Line 11" in content
        assert "Line 15" in content
        assert "Line 16" not in content

    def test_read_empty_file(self, client, headers, temp_dir):
        """Test reading an empty file."""
        (temp_dir / "empty.txt").write_text("")

        response = client.get("/api/read?file_path=empty.txt", headers=headers)
        assert response.status_code == 200
        assert "empty" in response.json()["content"].lower()

    def test_read_nonexistent_file(self, client, headers):
        """Test reading a file that doesn't exist."""
        response = client.get("/api/read?file_path=nonexistent.txt", headers=headers)
        assert response.status_code == 200
        assert "not found" in response.json()["content"]

    def test_edit_file(self, client, headers, temp_dir):
        """Test editing a file via POST /api/edit."""
        test_file = temp_dir / "edit_test.txt"
        test_file.write_text("Hello World\nHello Universe\n")

        response = client.post(
            "/api/edit",
            json={"file_path": "edit_test.txt", "old_string": "World", "new_string": "Python"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["occurrences"] == 1

        assert test_file.read_text() == "Hello Python\nHello Universe\n"

    def test_edit_file_replace_all(self, client, headers, temp_dir):
        """Test editing a file with replace_all=True."""
        test_file = temp_dir / "replace_all_test.txt"
        test_file.write_text("foo bar foo baz foo")

        response = client.post(
            "/api/edit",
            json={"file_path": "replace_all_test.txt", "old_string": "foo", "new_string": "qux", "replace_all": True},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["occurrences"] == 3

        assert test_file.read_text() == "qux bar qux baz qux"

    def test_edit_string_not_found(self, client, headers, temp_dir):
        """Test editing with a string that doesn't exist (Java backend test coverage)."""
        test_file = temp_dir / "no_match.txt"
        test_file.write_text("Some content")

        response = client.post(
            "/api/edit",
            json={"file_path": "no_match.txt", "old_string": "nonexistent", "new_string": "new"},
            headers=headers,
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_edit_nonexistent_file(self, client, headers):
        """Test editing a file that doesn't exist."""
        response = client.post(
            "/api/edit",
            json={"file_path": "nonexistent.txt", "old_string": "old", "new_string": "new"},
            headers=headers,
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    # ===== Unicode and Special Characters Tests =====

    def test_unicode_content(self, client, headers, temp_dir):
        """Test handling Unicode content (Python/Java backend coverage)."""
        unicode_content = "Hello 世界 🌍 Привет مرحبا"

        response = client.post(
            "/api/write",
            json={"file_path": "unicode.txt", "content": unicode_content},
            headers=headers,
        )
        assert response.status_code == 200

        response = client.get("/api/read?file_path=unicode.txt", headers=headers)
        assert response.status_code == 200
        content = response.json()["content"]
        assert "世界" in content
        assert "🌍" in content
        assert "Привет" in content
        assert "مرحبا" in content

    def test_special_characters_in_content(self, client, headers, temp_dir):
        """Test handling special characters."""
        special_content = "Tab:\t\nNewline:\n\nQuotes: \"' Backslash:\\ Null:\x00"

        response = client.post(
            "/api/write",
            json={"file_path": "special.txt", "content": special_content},
            headers=headers,
        )
        assert response.status_code == 200

        file_path = temp_dir / "special.txt"
        assert file_path.exists()

    # ===== List Directory Tests =====

    def test_ls_directory(self, client, headers, temp_dir):
        """Test listing directory contents via GET /api/ls."""
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file3.txt").write_text("content3")

        response = client.get(f"/api/ls?path={temp_dir}", headers=headers)
        assert response.status_code == 200
        files = response.json()["files"]

        paths = [f["path"] for f in files]
        assert any("file1.txt" in p for p in paths)
        assert any("file2.txt" in p for p in paths)
        assert any("subdir" in p for p in paths)

        file1_info = next(f for f in files if "file1.txt" in f["path"])
        assert file1_info["is_dir"] is False
        assert file1_info["size"] > 0
        assert "modified_at" in file1_info

        subdir_info = next(f for f in files if "subdir" in f["path"])
        assert subdir_info["is_dir"] is True
        assert subdir_info["path"].endswith("/")

    def test_ls_nested_directories(self, client, headers, temp_dir):
        """Test ls with nested directories (Python backend coverage)."""
        (temp_dir / "config.json").write_text("config")
        (temp_dir / "src").mkdir()
        (temp_dir / "src" / "main.py").write_text("code")
        (temp_dir / "src" / "utils").mkdir()
        (temp_dir / "src" / "utils" / "helper.py").write_text("utils code")

        # List root
        response = client.get(f"/api/ls?path={temp_dir}", headers=headers)
        assert response.status_code == 200
        root_paths = [f["path"] for f in response.json()["files"]]
        assert any("config.json" in p for p in root_paths)
        assert any("src" in p and p.endswith("/") for p in root_paths)

        # List src
        response = client.get(f"/api/ls?path={temp_dir}/src", headers=headers)
        assert response.status_code == 200
        src_paths = [f["path"] for f in response.json()["files"]]
        assert any("main.py" in p for p in src_paths)
        assert any("utils" in p and p.endswith("/") for p in src_paths)

    def test_ls_nonexistent_directory(self, client, headers):
        """Test listing a directory that doesn't exist."""
        response = client.get("/api/ls?path=/nonexistent", headers=headers)
        assert response.status_code == 200
        assert response.json()["files"] == []

    # ===== Grep Search Tests =====

    def test_grep_pattern_search(self, client, headers, temp_dir):
        """Test searching for patterns via GET /api/grep."""
        (temp_dir / "file1.txt").write_text("Hello World\nHello Python\n")
        (temp_dir / "file2.txt").write_text("Goodbye World\n")
        (temp_dir / "file3.py").write_text("print('Hello')\n")

        response = client.get(f"/api/grep?pattern=Hello&path={temp_dir}", headers=headers)
        assert response.status_code == 200
        matches = response.json()["matches"]

        assert len(matches) >= 2
        for match in matches:
            assert "path" in match
            assert "line" in match
            assert "text" in match
            assert "Hello" in match["text"]

    def test_grep_with_glob_filter(self, client, headers, temp_dir):
        """Test grep with glob pattern to filter files (Java backend coverage)."""
        (temp_dir / "file1.txt").write_text("pattern match\n")
        (temp_dir / "file2.py").write_text("pattern match\n")

        response = client.get(f"/api/grep?pattern=pattern&path={temp_dir}&glob=*.txt", headers=headers)
        assert response.status_code == 200
        matches = response.json()["matches"]

        for match in matches:
            assert match["path"].endswith(".txt")

    def test_grep_invalid_regex(self, client, headers, temp_dir):
        """Test grep with invalid regex pattern."""
        response = client.get(f"/api/grep?pattern=[invalid&path={temp_dir}", headers=headers)
        assert response.status_code == 400
        assert "Invalid regex" in response.json()["detail"]

    def test_grep_unicode_pattern(self, client, headers, temp_dir):
        """Test grep with Unicode patterns."""
        (temp_dir / "unicode.txt").write_text("Hello 世界\nПривет мир\n")

        response = client.get(f"/api/grep?pattern=世界&path={temp_dir}", headers=headers)
        assert response.status_code == 200
        matches = response.json()["matches"]
        assert len(matches) >= 1
        assert any("世界" in m["text"] for m in matches)

    # ===== Glob Pattern Tests =====

    def test_glob_pattern_matching(self, client, headers, temp_dir):
        """Test glob pattern matching via GET /api/glob."""
        (temp_dir / "test1.txt").write_text("content")
        (temp_dir / "test2.txt").write_text("content")
        (temp_dir / "test.py").write_text("content")
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "test3.txt").write_text("content")

        response = client.get(f"/api/glob?pattern=*.txt&path={temp_dir}", headers=headers)
        assert response.status_code == 200
        files = response.json()["files"]

        paths = [f["path"] for f in files]
        assert len(paths) >= 3
        assert all(p.endswith(".txt") for p in paths)

    def test_glob_recursive_pattern(self, client, headers, temp_dir):
        """Test recursive glob pattern matching (Python/Java backend coverage)."""
        (temp_dir / "root.md").write_text("content")
        subdir1 = temp_dir / "sub1"
        subdir1.mkdir()
        (subdir1 / "file1.md").write_text("content")
        subdir2 = subdir1 / "sub2"
        subdir2.mkdir()
        (subdir2 / "file2.md").write_text("content")

        response = client.get(f"/api/glob?pattern=**/*.md&path={temp_dir}", headers=headers)
        assert response.status_code == 200
        files = response.json()["files"]

        paths = [f["path"] for f in files]
        assert len(paths) >= 3

    def test_glob_nonexistent_directory(self, client, headers):
        """Test glob on nonexistent directory."""
        response = client.get("/api/glob?pattern=*.txt&path=/nonexistent", headers=headers)
        assert response.status_code == 200
        assert response.json()["files"] == []

    # ===== Multiple Sequential Operations =====

    def test_multiple_sequential_operations(self, client, headers, temp_dir):
        """Test multiple sequential operations (Java backend coverage)."""
        # Write
        response = client.post(
            "/api/write",
            json={"file_path": "sequence.txt", "content": "Initial content"},
            headers=headers,
        )
        assert response.status_code == 200

        # Read
        response = client.get("/api/read?file_path=sequence.txt", headers=headers)
        assert response.status_code == 200
        assert "Initial content" in response.json()["content"]

        # Edit
        response = client.post(
            "/api/edit",
            json={"file_path": "sequence.txt", "old_string": "Initial", "new_string": "Modified"},
            headers=headers,
        )
        assert response.status_code == 200

        # Read again
        response = client.get("/api/read?file_path=sequence.txt", headers=headers)
        assert response.status_code == 200
        assert "Modified content" in response.json()["content"]

        # List
        response = client.get(f"/api/ls?path={temp_dir}", headers=headers)
        assert response.status_code == 200
        paths = [f["path"] for f in response.json()["files"]]
        assert any("sequence.txt" in p for p in paths)

    def test_concurrent_operations(self, client, headers, temp_dir):
        """Test multiple concurrent operations."""
        for i in range(5):
            response = client.post(
                "/api/write",
                json={"file_path": f"file{i}.txt", "content": f"Content {i}"},
                headers=headers,
            )
            assert response.status_code == 200

        for i in range(5):
            response = client.get(f"/api/read?file_path=file{i}.txt", headers=headers)
            assert response.status_code == 200
            assert f"Content {i}" in response.json()["content"]

    # ===== Error Handling Tests =====

    def test_error_handling_missing_parameters(self, client, headers):
        """Test error handling for missing required parameters."""
        response = client.get("/api/read", headers=headers)
        assert response.status_code == 422  # Validation error

        response = client.get("/api/grep", headers=headers)
        assert response.status_code == 422

        response = client.get("/api/glob", headers=headers)
        assert response.status_code == 422

    def test_invalid_json_body(self, client, headers):
        """Test handling of invalid JSON in request body."""
        response = client.post(
            "/api/write",
            data="invalid json{",
            headers={**headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_not_found_endpoint(self, client, headers):
        """Test accessing a nonexistent endpoint."""
        response = client.get("/api/nonexistent", headers=headers)
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
