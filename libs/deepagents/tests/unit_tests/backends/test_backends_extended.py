"""Extended test cases for backend implementations with edge cases and stress tests."""

import os
import tempfile
from pathlib import Path

import pytest

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.state import StateBackend
from deepagents.backends.composite import CompositeBackend
from deepagents.backends.protocol import EditResult, WriteResult
from langchain.tools import ToolRuntime


def make_runtime(files=None):
    """Create a test runtime."""
    return ToolRuntime(
        state={
            "messages": [],
            "files": files or {},
        },
        context=None,
        tool_call_id="t1",
        store=None,
        stream_writer=lambda _: None,
        config={},
    )


class TestStateBackendExtended:
    """Extended tests for StateBackend."""

    def test_empty_file_operations(self):
        """Test operations on empty files."""
        rt = make_runtime()
        be = StateBackend(rt)

        # Write empty file
        res = be.write("/empty.txt", "")
        assert res.error is None
        rt.state["files"].update(res.files_update)

        # Read empty file
        content = be.read("/empty.txt")
        assert "empty" in content.lower() or content == ""

        # Edit empty file
        edit_res = be.edit("/empty.txt", "nonexistent", "new")
        assert edit_res.error is not None

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters."""
        rt = make_runtime()
        be = StateBackend(rt)

        unicode_content = "Hello 世界 🌍 Привет\nSpecial: <>&\"'\t\n"
        res = be.write("/unicode.txt", unicode_content)
        assert res.error is None
        rt.state["files"].update(res.files_update)

        content = be.read("/unicode.txt")
        assert "世界" in content
        assert "🌍" in content
        assert "Привет" in content

        # Search for Unicode
        matches = be.grep_raw("世界", path="/")
        assert len(matches) > 0
        assert any("世界" in m["text"] for m in matches)

    def test_large_content(self):
        """Test handling of large file content."""
        rt = make_runtime()
        be = StateBackend(rt)

        # Create large content (10,000 lines)
        large_content = "\n".join([f"Line {i}" for i in range(10000)])
        res = be.write("/large.txt", large_content)
        assert res.error is None
        rt.state["files"].update(res.files_update)

        # Read with offset and limit
        content = be.read("/large.txt", offset=5000, limit=10)
        assert "Line 5000" in content
        assert "Line 5009" in content
        assert "Line 5010" not in content

    def test_many_files(self):
        """Test handling many files."""
        rt = make_runtime()
        be = StateBackend(rt)

        # Create 100 files
        for i in range(100):
            res = be.write(f"/file{i}.txt", f"Content {i}")
            assert res.error is None
            rt.state["files"].update(res.files_update)

        # List should show all files
        listing = be.ls_info("/")
        assert len(listing) == 100

        # Glob should find all txt files
        glob_result = be.glob_info("*.txt", "/")
        assert len(glob_result) == 100

    def test_deep_nesting(self):
        """Test deeply nested directory structures."""
        rt = make_runtime()
        be = StateBackend(rt)

        # Create deeply nested file (10 levels)
        deep_path = "/".join([f"level{i}" for i in range(10)]) + "/deep.txt"
        res = be.write("/" + deep_path, "Deep content")
        assert res.error is None
        rt.state["files"].update(res.files_update)

        # Read it back
        content = be.read("/" + deep_path)
        assert "Deep content" in content

        # List should work at each level
        current_path = "/"
        for i in range(10):
            listing = be.ls_info(current_path)
            assert len(listing) > 0
            current_path += f"level{i}/"

    def test_replace_all_with_multiple_occurrences(self):
        """Test replace_all with multiple occurrences."""
        rt = make_runtime()
        be = StateBackend(rt)

        content = "foo bar foo baz foo qux foo"
        res = be.write("/multi.txt", content)
        rt.state["files"].update(res.files_update)

        # Replace all
        edit_res = be.edit("/multi.txt", "foo", "FOO", replace_all=True)
        assert edit_res.error is None
        assert edit_res.occurrences == 4
        rt.state["files"].update(edit_res.files_update)

        # Verify
        new_content = be.read("/multi.txt")
        assert "FOO" in new_content
        assert "foo" not in new_content

    def test_string_not_found_in_edit(self):
        """Test edit when string is not found."""
        rt = make_runtime()
        be = StateBackend(rt)

        res = be.write("/test.txt", "Some content here")
        rt.state["files"].update(res.files_update)

        edit_res = be.edit("/test.txt", "nonexistent", "new")
        assert edit_res.error is not None
        assert "not found" in edit_res.error

    def test_grep_with_regex_patterns(self):
        """Test grep with various regex patterns."""
        rt = make_runtime()
        be = StateBackend(rt)

        res = be.write("/test.py", "def foo():\n    return 42\n\nclass Bar:\n    pass")
        rt.state["files"].update(res.files_update)

        # Match function definitions
        matches = be.grep_raw(r"def\s+\w+", path="/")
        assert len(matches) > 0

        # Match class definitions
        matches = be.grep_raw(r"class\s+\w+", path="/")
        assert len(matches) > 0

        # Invalid regex
        result = be.grep_raw("[invalid", path="/")
        assert isinstance(result, str)
        assert "invalid" in result.lower() or "error" in result.lower()

    def test_glob_recursive_patterns(self):
        """Test glob with recursive patterns."""
        rt = make_runtime()
        be = StateBackend(rt)

        # Create nested structure
        files = {
            "/root.md": "root",
            "/sub1/file1.md": "file1",
            "/sub1/sub2/file2.md": "file2",
            "/sub1/sub2/sub3/file3.md": "file3",
        }

        for path, content in files.items():
            res = be.write(path, content)
            rt.state["files"].update(res.files_update)

        # Recursive glob
        glob_result = be.glob_info("**/*.md", "/")
        assert len(glob_result) == 4

    def test_concurrent_write_operations(self):
        """Test multiple concurrent-like operations."""
        rt = make_runtime()
        be = StateBackend(rt)

        # Write multiple files in sequence
        for i in range(10):
            res = be.write(f"/concurrent{i}.txt", f"Content {i}")
            assert res.error is None
            rt.state["files"].update(res.files_update)

            # Immediate read
            content = be.read(f"/concurrent{i}.txt")
            assert f"Content {i}" in content


class TestFilesystemBackendExtended:
    """Extended tests for FilesystemBackend."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_symlink_handling(self, temp_dir):
        """Test handling of symbolic links."""
        be = FilesystemBackend(root_dir=str(temp_dir), virtual_mode=True)

        # Create a file and a symlink to it
        real_file = temp_dir / "real.txt"
        real_file.write_text("Real content")

        symlink_file = temp_dir / "link.txt"
        if os.name != "nt":  # Skip on Windows
            symlink_file.symlink_to(real_file)

            # Ls should list both
            listing = be.ls_info("/")
            paths = [f["path"] for f in listing]
            assert "/real.txt" in paths

            # Read should work through symlink
            if symlink_file.exists():
                content = be.read("/link.txt")
                assert "Real content" in content

    def test_permission_error_handling(self, temp_dir):
        """Test handling of permission errors."""
        if os.name == "nt":
            pytest.skip("Permission test not reliable on Windows")

        be = FilesystemBackend(root_dir=str(temp_dir), virtual_mode=True)

        # Create a file
        test_file = temp_dir / "readonly.txt"
        test_file.write_text("Content")

        # Make it read-only
        test_file.chmod(0o444)

        try:
            # Try to write to it (should fail)
            edit_res = be.edit("/readonly.txt", "Content", "New")
            # Should handle gracefully
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)

    def test_large_file_grep(self, temp_dir):
        """Test grep on large files."""
        be = FilesystemBackend(root_dir=str(temp_dir), virtual_mode=True)

        # Create a large file (within size limit)
        large_file = temp_dir / "large.txt"
        lines = [f"Line {i} with pattern{i}" for i in range(1000)]
        large_file.write_text("\n".join(lines))

        # Grep should work
        matches = be.grep_raw("pattern500", path="/")
        assert len(matches) > 0
        assert any("pattern500" in m["text"] for m in matches)

    def test_binary_file_handling(self, temp_dir):
        """Test handling of binary files."""
        be = FilesystemBackend(root_dir=str(temp_dir), virtual_mode=True)

        # Create a binary file
        binary_file = temp_dir / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

        # Read should handle gracefully (might return error)
        result = be.read("/binary.bin")
        # Should not crash, might return error message

    def test_path_traversal_protection(self, temp_dir):
        """Test that path traversal is blocked."""
        be = FilesystemBackend(root_dir=str(temp_dir), virtual_mode=True)

        # Try various path traversal attempts
        with pytest.raises(ValueError):
            be.read("/../etc/passwd")

        with pytest.raises(ValueError):
            be.write("/../malicious.txt", "bad")

        with pytest.raises(ValueError):
            be.edit("/../test.txt", "old", "new")

    def test_special_filenames(self, temp_dir):
        """Test handling of special filenames."""
        be = FilesystemBackend(root_dir=str(temp_dir), virtual_mode=True)

        # Filenames with spaces and special chars
        special_names = [
            "/file with spaces.txt",
            "/file-with-dashes.txt",
            "/file_with_underscores.txt",
            "/file.multiple.dots.txt",
        ]

        for name in special_names:
            res = be.write(name, "Content")
            if res.error is None:  # If successfully created
                content = be.read(name)
                assert "Content" in content

    def test_empty_directory_operations(self, temp_dir):
        """Test operations on empty directories."""
        be = FilesystemBackend(root_dir=str(temp_dir), virtual_mode=True)

        # Create empty directory
        (temp_dir / "empty").mkdir()

        # List should return empty
        listing = be.ls_info("/empty/")
        assert listing == []

        # Glob in empty directory
        glob_result = be.glob_info("*", "/empty")
        assert glob_result == []


class TestCompositeBackendExtended:
    """Extended tests for CompositeBackend."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_prefix_routing(self, temp_dir):
        """Test routing based on path prefixes."""
        rt = make_runtime()
        state_be = StateBackend(rt)
        state_be2 = StateBackend(rt)

        composite = CompositeBackend(
            default=state_be,
            routes={
                "/state": state_be,
                "/memory": state_be2,
            },
        )

        # Write to state backend
        res1 = composite.write("/state/file1.txt", "State content")
        assert res1.error is None
        rt.state["files"].update(res1.files_update)

        # Write to memory backend
        res2 = composite.write("/memory/file2.txt", "Memory content")
        assert res2.error is None
        rt.state["files"].update(res2.files_update)

        # Read back from each
        content1 = composite.read("/state/file1.txt")
        assert "State content" in content1

        content2 = composite.read("/memory/file2.txt")
        assert "Memory content" in content2

    def test_fallback_to_default(self):
        """Test fallback to default backend."""
        rt = make_runtime()
        state_be = StateBackend(rt)

        composite = CompositeBackend(
            default=state_be,
            routes={"/special": state_be},
        )

        # Unmatched prefix should use default
        res = composite.write("/other/file.txt", "Content")
        assert res.error is None
        rt.state["files"].update(res.files_update)

        content = composite.read("/other/file.txt")
        assert "Content" in content

    def test_multiple_backend_types(self, temp_dir):
        """Test mixing different backend types."""
        rt = make_runtime()
        state_be = StateBackend(rt)
        state_be2 = StateBackend(rt)

        composite = CompositeBackend(
            default=state_be,
            routes={
                "/memory": state_be,
                "/cache": state_be2,
            },
        )

        # Write to both backends with different filenames
        res1 = composite.write("/memory/data1.txt", "Memory data")
        rt.state["files"].update(res1.files_update)

        res2 = composite.write("/cache/data2.txt", "Cache data")
        assert res2.error is None
        rt.state["files"].update(res2.files_update)

        # List each
        mem_listing = composite.ls_info("/memory")
        cache_listing = composite.ls_info("/cache")

        assert len(mem_listing) > 0
        assert len(cache_listing) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
