"""Standalone HTTP file server exposing BackendProtocol operations.

This module provides an independent HTTP server that exposes filesystem operations
through a RESTful API without external dependencies (uses only Python standard library).
"""

import json
import os
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import parse_qs, urlparse


class FileInfo(TypedDict, total=False):
    """File information structure."""

    path: str
    is_dir: bool
    size: int
    modified_at: str


class GrepMatch(TypedDict):
    """Grep match structure."""

    path: str
    line: int
    text: str


class WriteResult(TypedDict, total=False):
    """Write operation result."""

    error: str | None
    path: str | None


class EditResult(TypedDict, total=False):
    """Edit operation result."""

    error: str | None
    path: str | None
    occurrences: int | None


class FilesystemBackend:
    """Minimal filesystem backend implementation using only standard library."""

    def __init__(self, root_dir: str | Path | None = None, max_file_size_mb: int = 10) -> None:
        """Initialize filesystem backend.

        Args:
            root_dir: Root directory for file operations. Defaults to current working directory.
            max_file_size_mb: Maximum file size in MB for grep operations.
        """
        self.cwd = Path(root_dir).resolve() if root_dir else Path.cwd()
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def _resolve_path(self, key: str) -> Path:
        """Resolve a file path relative to root directory.

        Args:
            key: File path (absolute or relative)

        Returns:
            Resolved absolute Path object
        """
        path = Path(key)
        if path.is_absolute():
            return path
        return (self.cwd / path).resolve()

    def ls_info(self, path: str) -> list[FileInfo]:
        """List files and directories in the specified directory.

        Args:
            path: Directory path to list files from.

        Returns:
            List of FileInfo dicts for files and directories.
        """
        dir_path = self._resolve_path(path)
        if not dir_path.exists() or not dir_path.is_dir():
            return []

        results: list[FileInfo] = []

        try:
            for child_path in dir_path.iterdir():
                try:
                    is_file = child_path.is_file()
                    is_dir = child_path.is_dir()
                except OSError:
                    continue

                abs_path = str(child_path)

                if is_file:
                    try:
                        st = child_path.stat()
                        results.append(
                            {
                                "path": abs_path,
                                "is_dir": False,
                                "size": int(st.st_size),
                                "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                            }
                        )
                    except OSError:
                        results.append({"path": abs_path, "is_dir": False})
                elif is_dir:
                    try:
                        st = child_path.stat()
                        results.append(
                            {
                                "path": abs_path + "/",
                                "is_dir": True,
                                "size": 0,
                                "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                            }
                        )
                    except OSError:
                        results.append({"path": abs_path + "/", "is_dir": True})
        except (OSError, PermissionError):
            pass

        results.sort(key=lambda x: x.get("path", ""))
        return results

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file content with line numbers.

        Args:
            file_path: File path to read
            offset: Line offset to start reading from (0-indexed)
            limit: Maximum number of lines to read

        Returns:
            Formatted file content with line numbers, or error message.
        """
        resolved_path = self._resolve_path(file_path)

        if not resolved_path.exists() or not resolved_path.is_file():
            return f"Error: File '{file_path}' not found"

        try:
            with open(resolved_path, encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                return "File is empty"

            lines = content.splitlines()
            start_idx = offset
            end_idx = min(start_idx + limit, len(lines))

            if start_idx >= len(lines):
                return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

            selected_lines = lines[start_idx:end_idx]
            formatted_lines = []
            for i, line in enumerate(selected_lines, start=start_idx + 1):
                formatted_lines.append(f"{i:5d} | {line}")

            return "\n".join(formatted_lines)
        except (OSError, UnicodeDecodeError) as e:
            return f"Error reading file '{file_path}': {e}"

    def write(self, file_path: str, content: str) -> WriteResult:
        """Create a new file with content.

        Args:
            file_path: Path to create the file
            content: File content

        Returns:
            WriteResult with error or path
        """
        resolved_path = self._resolve_path(file_path)

        if resolved_path.exists():
            return {
                "error": f"Cannot write to {file_path} because it already exists. Read and then make an edit, or write to a new path.",
                "path": None,
            }

        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"error": None, "path": file_path}
        except (OSError, UnicodeEncodeError) as e:
            return {"error": f"Error writing file '{file_path}': {e}", "path": None}

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        """Edit a file by replacing string occurrences.

        Args:
            file_path: Path to the file to edit
            old_string: String to replace
            new_string: Replacement string
            replace_all: If True, replace all occurrences; otherwise replace only first

        Returns:
            EditResult with error, path, and number of occurrences replaced
        """
        resolved_path = self._resolve_path(file_path)

        if not resolved_path.exists() or not resolved_path.is_file():
            return {"error": f"Error: File '{file_path}' not found", "path": None, "occurrences": None}

        try:
            with open(resolved_path, encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return {
                    "error": f"String '{old_string[:50]}...' not found in file",
                    "path": None,
                    "occurrences": None,
                }

            if replace_all:
                new_content = content.replace(old_string, new_string)
                occurrences = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                occurrences = 1

            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {"error": None, "path": file_path, "occurrences": occurrences}
        except (OSError, UnicodeDecodeError, UnicodeEncodeError) as e:
            return {"error": f"Error editing file '{file_path}': {e}", "path": None, "occurrences": None}

    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[GrepMatch] | str:
        """Search for pattern in files.

        Args:
            pattern: Regular expression pattern to search for
            path: Base path to search in (defaults to current directory)
            glob: Glob pattern to filter files (e.g., "*.py")

        Returns:
            List of GrepMatch dicts or error string
        """
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Invalid regex pattern: {e}"

        try:
            base_full = self._resolve_path(path or ".")
        except ValueError:
            return []

        if not base_full.exists():
            return []

        results: dict[str, list[tuple[int, str]]] = {}
        root = base_full if base_full.is_dir() else base_full.parent

        for fp in root.rglob("*"):
            if not fp.is_file():
                continue
            if glob and not self._glob_match(fp.name, glob):
                continue
            try:
                if fp.stat().st_size > self.max_file_size_bytes:
                    continue
            except OSError:
                continue
            try:
                content = fp.read_text()
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
            for line_num, line in enumerate(content.splitlines(), 1):
                if regex.search(line):
                    virt_path = str(fp)
                    results.setdefault(virt_path, []).append((line_num, line))

        matches: list[GrepMatch] = []
        for fpath, items in results.items():
            for line_num, line_text in items:
                matches.append({"path": fpath, "line": int(line_num), "text": line_text})
        return matches

    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.py", "**/*.txt")
            path: Base path to search from

        Returns:
            List of FileInfo dicts for matching files
        """
        if pattern.startswith("/"):
            pattern = pattern.lstrip("/")

        search_path = self.cwd if path == "/" else self._resolve_path(path)
        if not search_path.exists() or not search_path.is_dir():
            return []

        results: list[FileInfo] = []
        try:
            for matched_path in search_path.rglob(pattern):
                try:
                    is_file = matched_path.is_file()
                except OSError:
                    continue
                if not is_file:
                    continue
                abs_path = str(matched_path)
                try:
                    st = matched_path.stat()
                    results.append(
                        {
                            "path": abs_path,
                            "is_dir": False,
                            "size": int(st.st_size),
                            "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        }
                    )
                except OSError:
                    results.append({"path": abs_path, "is_dir": False})
        except (OSError, ValueError):
            pass

        results.sort(key=lambda x: x.get("path", ""))
        return results

    def _glob_match(self, name: str, pattern: str) -> bool:
        """Simple glob pattern matching for filenames."""
        import fnmatch

        return fnmatch.fnmatch(name, pattern)


class FileServerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for file server operations."""

    backend: FilesystemBackend

    def _set_headers(self, status: int = 200, content_type: str = "application/json") -> None:
        """Set response headers."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Send JSON response."""
        self._set_headers(status)
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def _send_error_json(self, message: str, status: int = 400) -> None:
        """Send error response."""
        self._send_json({"error": message}, status)

    def _parse_body(self) -> dict[str, Any]:
        """Parse JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode("utf-8"))

    def do_OPTIONS(self) -> None:
        """Handle OPTIONS requests for CORS."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        params = parse_qs(parsed_url.query)

        try:
            if path == "/health":
                self._send_json({"status": "ok"})
            elif path == "/api/ls":
                dir_path = params.get("path", ["."])[0]
                result = self.backend.ls_info(dir_path)
                self._send_json({"files": result})
            elif path == "/api/read":
                file_path = params.get("file_path", [""])[0]
                if not file_path:
                    self._send_error_json("file_path parameter is required")
                    return
                offset = int(params.get("offset", ["0"])[0])
                limit = int(params.get("limit", ["2000"])[0])
                result = self.backend.read(file_path, offset, limit)
                self._send_json({"content": result})
            elif path == "/api/grep":
                pattern = params.get("pattern", [""])[0]
                if not pattern:
                    self._send_error_json("pattern parameter is required")
                    return
                search_path = params.get("path", [None])[0]
                glob_pattern = params.get("glob", [None])[0]
                result = self.backend.grep_raw(pattern, search_path, glob_pattern)
                if isinstance(result, str):
                    self._send_error_json(result)
                else:
                    self._send_json({"matches": result})
            elif path == "/api/glob":
                pattern = params.get("pattern", [""])[0]
                if not pattern:
                    self._send_error_json("pattern parameter is required")
                    return
                search_path = params.get("path", ["/"])[0]
                result = self.backend.glob_info(pattern, search_path)
                self._send_json({"files": result})
            else:
                self._send_error_json("Not found", 404)
        except Exception as e:
            self._send_error_json(f"Internal server error: {e}", 500)

    def do_POST(self) -> None:
        """Handle POST requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        try:
            if path == "/api/write":
                data = self._parse_body()
                file_path = data.get("file_path", "")
                content = data.get("content", "")
                if not file_path:
                    self._send_error_json("file_path is required")
                    return
                result = self.backend.write(file_path, content)
                if result.get("error"):
                    self._send_error_json(result["error"])
                else:
                    self._send_json(result)
            elif path == "/api/edit":
                data = self._parse_body()
                file_path = data.get("file_path", "")
                old_string = data.get("old_string", "")
                new_string = data.get("new_string", "")
                replace_all = data.get("replace_all", False)
                if not file_path or not old_string:
                    self._send_error_json("file_path and old_string are required")
                    return
                result = self.backend.edit(file_path, old_string, new_string, replace_all)
                if result.get("error"):
                    self._send_error_json(result["error"])
                else:
                    self._send_json(result)
            else:
                self._send_error_json("Not found", 404)
        except json.JSONDecodeError:
            self._send_error_json("Invalid JSON")
        except Exception as e:
            self._send_error_json(f"Internal server error: {e}", 500)

    def log_message(self, format: str, *args: Any) -> None:
        """Override to customize logging."""
        print(f"[{self.log_date_time_string()}] {format % args}")


class FileServer:
    """HTTP file server exposing BackendProtocol operations."""

    def __init__(self, root_dir: str | Path | None = None, host: str = "localhost", port: int = 8080) -> None:
        """Initialize file server.

        Args:
            root_dir: Root directory for file operations
            host: Server host address
            port: Server port number
        """
        self.root_dir = root_dir
        self.host = host
        self.port = port
        self.backend = FilesystemBackend(root_dir)
        self.server: HTTPServer | None = None

    def start(self) -> None:
        """Start the HTTP server."""
        FileServerHandler.backend = self.backend
        self.server = HTTPServer((self.host, self.port), FileServerHandler)
        print(f"FileServer started at http://{self.host}:{self.port}")
        print(f"Root directory: {self.backend.cwd}")
        print("\nAvailable endpoints:")
        print("  GET  /health              - Health check")
        print("  GET  /api/ls              - List directory (params: path)")
        print("  GET  /api/read            - Read file (params: file_path, offset, limit)")
        print("  GET  /api/grep            - Search files (params: pattern, path, glob)")
        print("  GET  /api/glob            - Glob pattern match (params: pattern, path)")
        print("  POST /api/write           - Write file (body: file_path, content)")
        print("  POST /api/edit            - Edit file (body: file_path, old_string, new_string, replace_all)")
        print("\nPress Ctrl+C to stop the server")
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            self.stop()

    def stop(self) -> None:
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("Server stopped")


def main() -> None:
    """Main entry point for running the file server."""
    import sys

    root_dir = sys.argv[1] if len(sys.argv) > 1 else None
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

    server = FileServer(root_dir=root_dir, port=port)
    server.start()


if __name__ == "__main__":
    main()
