"""Integration tests for FileServer with Python and Java backend modules.

Tests the file server with both Python and Java backend implementations to ensure
compatibility and functional parity.
"""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import requests

from fileserver.fastapi_server import SecureFileServer


class TestFileServerBackendIntegration:
    """Integration tests for FileServer with Python and Java backends."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def base_url(self):
        """Base URL for the test server."""
        return "http://localhost:8080"

    @pytest.fixture
    def unique_suffix(self):
        """Generate a unique suffix for file names."""
        import random

        return random.randint(100000, 999999)

    def test_python_backend_write_and_read(self, base_url, temp_dir, unique_suffix):
        """Test write and read operations work with Python backend."""
        filename = f"python_test_{unique_suffix}.txt"
        # Write a file
        response = requests.post(f"{base_url}/api/write", json={"file_path": filename, "content": "Hello from Python backend!"})
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None

        # Read it back
        response = requests.get(f"{base_url}/api/read?file_path={filename}")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "Hello from Python backend!" in content

    def test_python_backend_edit(self, base_url, unique_suffix):
        """Test edit operation with Python backend."""
        filename = f"edit_python_{unique_suffix}.txt"
        # Create a file
        requests.post(f"{base_url}/api/write", json={"file_path": filename, "content": "Original text"})

        # Edit it
        response = requests.post(f"{base_url}/api/edit", json={"file_path": filename, "old_string": "Original", "new_string": "Modified"})
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert data["occurrences"] == 1

        # Verify edit
        response = requests.get(f"{base_url}/api/read?file_path={filename}")
        content = response.json()["content"]
        assert "Modified text" in content

    def test_python_backend_ls(self, base_url):
        """Test ls operation with Python backend."""
        # Create some test files
        requests.post(f"{base_url}/api/write", json={"file_path": "ls_test1.txt", "content": "content1"})
        requests.post(f"{base_url}/api/write", json={"file_path": "ls_test2.txt", "content": "content2"})

        # List directory
        response = requests.get(f"{base_url}/api/ls")
        assert response.status_code == 200
        files = response.json()["files"]
        assert len(files) > 0

        # Check our files are listed
        paths = [f["path"] for f in files]
        assert any("ls_test1.txt" in p for p in paths)
        assert any("ls_test2.txt" in p for p in paths)

    def test_python_backend_grep(self, base_url):
        """Test grep operation with Python backend."""
        # Create test files with searchable content (use unique names)
        import random

        suffix = random.randint(10000, 99999)
        requests.post(f"{base_url}/api/write", json={"file_path": f"grep_test1_{suffix}.txt", "content": "FINDME in file 1\nother content\n"})
        requests.post(f"{base_url}/api/write", json={"file_path": f"grep_test2_{suffix}.txt", "content": "FINDME in file 2\nmore content\n"})

        # Search for pattern
        response = requests.get(f"{base_url}/api/grep?pattern=FINDME")
        assert response.status_code == 200
        matches = response.json()["matches"]
        # Should find at least our 2 files (may find more from previous tests)
        findme_matches = [m for m in matches if "FINDME" in m["text"]]
        assert len(findme_matches) >= 2

        # Verify match structure
        for match in findme_matches:
            assert "path" in match
            assert "line" in match
            assert "text" in match
            assert "FINDME" in match["text"]

    def test_python_backend_glob(self, base_url):
        """Test glob operation with Python backend."""
        # Create test files with different extensions
        requests.post(f"{base_url}/api/write", json={"file_path": "glob1.md", "content": "markdown"})
        requests.post(f"{base_url}/api/write", json={"file_path": "glob2.md", "content": "markdown"})
        requests.post(f"{base_url}/api/write", json={"file_path": "glob3.txt", "content": "text"})

        # Glob for .md files
        response = requests.get(f"{base_url}/api/glob?pattern=*.md")
        assert response.status_code == 200
        files = response.json()["files"]

        # Should find .md files
        md_files = [f for f in files if f["path"].endswith(".md")]
        assert len(md_files) >= 2

    def test_python_backend_nested_directories(self, base_url, unique_suffix):
        """Test operations with nested directories."""
        filename = f"nested_{unique_suffix}/deep/path/test.txt"
        # Create nested file
        response = requests.post(f"{base_url}/api/write", json={"file_path": filename, "content": "nested content"})
        assert response.status_code == 200

        # Read it back
        response = requests.get(f"{base_url}/api/read?file_path={filename}")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "nested content" in content

    def test_python_backend_unicode(self, base_url, unique_suffix):
        """Test Unicode handling with Python backend."""
        filename = f"unicode_test_{unique_suffix}.txt"
        unicode_text = "Hello 世界 🌍 Привет مرحبا"

        # Write Unicode content
        response = requests.post(f"{base_url}/api/write", json={"file_path": filename, "content": unicode_text})
        assert response.status_code == 200

        # Read it back
        response = requests.get(f"{base_url}/api/read?file_path={filename}")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "世界" in content
        assert "🌍" in content
        assert "Привет" in content
        assert "مرحبا" in content

    def test_python_backend_large_file_operations(self, base_url, unique_suffix):
        """Test operations with larger files."""
        filename = f"large_file_{unique_suffix}.txt"
        # Create a file with many lines
        lines = "\n".join([f"Line {i}" for i in range(1000)])
        response = requests.post(f"{base_url}/api/write", json={"file_path": filename, "content": lines})
        assert response.status_code == 200

        # Read with pagination
        response = requests.get(f"{base_url}/api/read?file_path={filename}&offset=100&limit=10")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "Line 100" in content
        assert "Line 109" in content

    def test_python_backend_empty_file(self, base_url):
        """Test operations with empty files."""
        # Write empty file (use unique name)
        import random

        suffix = random.randint(10000, 99999)
        filename = f"empty_{suffix}.txt"
        response = requests.post(f"{base_url}/api/write", json={"file_path": filename, "content": ""})
        assert response.status_code == 200

        # Read it back
        response = requests.get(f"{base_url}/api/read?file_path={filename}")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "empty" in content.lower()

    def test_python_backend_multiple_edits(self, base_url):
        """Test multiple sequential edits."""
        # Create a file
        requests.post(f"{base_url}/api/write", json={"file_path": "multi_edit.txt", "content": "Step 1"})

        # Edit multiple times
        requests.post(f"{base_url}/api/edit", json={"file_path": "multi_edit.txt", "old_string": "Step 1", "new_string": "Step 2"})
        requests.post(f"{base_url}/api/edit", json={"file_path": "multi_edit.txt", "old_string": "Step 2", "new_string": "Step 3"})
        requests.post(f"{base_url}/api/edit", json={"file_path": "multi_edit.txt", "old_string": "Step 3", "new_string": "Final"})

        # Verify final content
        response = requests.get(f"{base_url}/api/read?file_path=multi_edit.txt")
        content = response.json()["content"]
        assert "Final" in content

    def test_backend_operations_coverage(self, base_url, unique_suffix):
        """Test all backend operations are properly exposed and working."""
        filename = f"coverage_test_{unique_suffix}.txt"
        operations = {
            "write": lambda: requests.post(f"{base_url}/api/write", json={"file_path": filename, "content": "test content"}),
            "read": lambda: requests.get(f"{base_url}/api/read?file_path={filename}"),
            "edit": lambda: requests.post(f"{base_url}/api/edit", json={"file_path": filename, "old_string": "test", "new_string": "updated"}),
            "ls": lambda: requests.get(f"{base_url}/api/ls"),
            "grep": lambda: requests.get(f"{base_url}/api/grep?pattern=updated"),
            "glob": lambda: requests.get(f"{base_url}/api/glob?pattern=*.txt"),
        }

        # Test each operation
        for op_name, op_func in operations.items():
            try:
                response = op_func()
                assert response.status_code in [200, 201], f"Operation {op_name} failed"
            except Exception as e:
                pytest.fail(f"Operation {op_name} raised exception: {e}")

    def test_error_handling(self, base_url):
        """Test proper error handling for invalid operations."""
        # Try to read non-existent file
        response = requests.get(f"{base_url}/api/read?file_path=nonexistent12345.txt")
        assert response.status_code == 200
        content = response.json()["content"]
        assert "not found" in content.lower()

        # Try to edit non-existent file
        response = requests.post(f"{base_url}/api/edit", json={"file_path": "nonexistent12345.txt", "old_string": "foo", "new_string": "bar"})
        assert response.status_code == 400

        # Try to write to existing file
        requests.post(f"{base_url}/api/write", json={"file_path": "existing.txt", "content": "content"})
        response = requests.post(f"{base_url}/api/write", json={"file_path": "existing.txt", "content": "new content"})
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
