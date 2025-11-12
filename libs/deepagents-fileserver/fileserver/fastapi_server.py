"""FastAPI-based file server with security features.

This module provides a production-ready HTTP server using FastAPI with:
- API key authentication
- Rate limiting
- Path traversal protection
- Request validation
- Comprehensive error handling
"""

import os
import re
import secrets
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn


class FileInfo(BaseModel):
    """File information structure."""

    path: str
    is_dir: bool
    size: int = 0
    modified_at: str = ""


class GrepMatch(BaseModel):
    """Grep match structure."""

    path: str
    line: int
    text: str


class WriteRequest(BaseModel):
    """Request model for write operation."""

    file_path: str = Field(..., min_length=1, description="Path where the file should be created")
    content: str = Field(default="", description="Content to write to the file")

    @field_validator("file_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate and sanitize file path."""
        if ".." in v or v.startswith("/"):
            raise ValueError("Invalid path: path traversal or absolute paths not allowed")
        return v


class WriteResponse(BaseModel):
    """Response model for write operation."""

    error: Optional[str] = None
    path: Optional[str] = None


class EditRequest(BaseModel):
    """Request model for edit operation."""

    file_path: str = Field(..., min_length=1, description="Path to the file to edit")
    old_string: str = Field(..., min_length=1, description="String to replace")
    new_string: str = Field(default="", description="Replacement string")
    replace_all: bool = Field(default=False, description="Replace all occurrences")

    @field_validator("file_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate and sanitize file path."""
        if ".." in v or v.startswith("/"):
            raise ValueError("Invalid path: path traversal or absolute paths not allowed")
        return v


class EditResponse(BaseModel):
    """Response model for edit operation."""

    error: Optional[str] = None
    path: Optional[str] = None
    occurrences: Optional[int] = None


class LsResponse(BaseModel):
    """Response model for ls operation."""

    files: list[FileInfo]


class ReadResponse(BaseModel):
    """Response model for read operation."""

    content: str


class GrepResponse(BaseModel):
    """Response model for grep operation."""

    matches: list[GrepMatch]


class GlobResponse(BaseModel):
    """Response model for glob operation."""

    files: list[FileInfo]


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    uptime: float
    version: str = "2.0.0"


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for the client.

        Args:
            client_id: Client identifier (IP address or API key)

        Returns:
            True if request is allowed, False otherwise
        """
        with self.lock:
            now = time.time()
            # Clean up old requests
            self.requests[client_id] = [req_time for req_time in self.requests[client_id] if now - req_time < self.window_seconds]

            if len(self.requests[client_id]) >= self.max_requests:
                return False

            self.requests[client_id].append(now)
            return True


class FilesystemBackend:
    """Secure filesystem backend with path traversal protection."""

    def __init__(self, root_dir: str | Path | None = None, max_file_size_mb: int = 10) -> None:
        """Initialize filesystem backend.

        Args:
            root_dir: Root directory for file operations
            max_file_size_mb: Maximum file size in MB for grep operations
        """
        self.cwd = Path(root_dir).resolve() if root_dir else Path.cwd()
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def _resolve_path(self, key: str) -> Path:
        """Resolve and validate file path with traversal protection.

        Args:
            key: File path (relative only)

        Returns:
            Resolved absolute Path object

        Raises:
            ValueError: If path traversal is detected
        """
        if key.startswith("/"):
            key = key.lstrip("/")

        resolved = (self.cwd / key).resolve()

        # Check for path traversal
        try:
            resolved.relative_to(self.cwd)
        except ValueError:
            raise ValueError(f"Path traversal detected: {key}")

        return resolved

    def ls_info(self, path: str) -> list[dict[str, Any]]:
        """List files and directories."""
        try:
            dir_path = self._resolve_path(path) if path != "." else self.cwd
        except ValueError:
            return []

        if not dir_path.exists() or not dir_path.is_dir():
            return []

        results: list[dict[str, Any]] = []

        try:
            for child_path in sorted(dir_path.iterdir()):
                try:
                    is_file = child_path.is_file()
                    is_dir = child_path.is_dir()
                except OSError:
                    continue

                rel_path = str(child_path.relative_to(self.cwd))

                if is_file:
                    try:
                        st = child_path.stat()
                        results.append(
                            {
                                "path": rel_path,
                                "is_dir": False,
                                "size": int(st.st_size),
                                "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                            }
                        )
                    except OSError:
                        results.append({"path": rel_path, "is_dir": False, "size": 0, "modified_at": ""})
                elif is_dir:
                    try:
                        st = child_path.stat()
                        results.append(
                            {
                                "path": rel_path + "/",
                                "is_dir": True,
                                "size": 0,
                                "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                            }
                        )
                    except OSError:
                        results.append({"path": rel_path + "/", "is_dir": True, "size": 0, "modified_at": ""})
        except (OSError, PermissionError):
            pass

        return results

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file content with line numbers."""
        try:
            resolved_path = self._resolve_path(file_path)
        except ValueError as e:
            return f"Error: {e}"

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

    def write(self, file_path: str, content: str) -> dict[str, Any]:
        """Create a new file with content."""
        try:
            resolved_path = self._resolve_path(file_path)
        except ValueError as e:
            return {"error": str(e), "path": None}

        if resolved_path.exists():
            return {
                "error": f"Cannot write to {file_path} because it already exists.",
                "path": None,
            }

        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"error": None, "path": file_path}
        except (OSError, UnicodeEncodeError) as e:
            return {"error": f"Error writing file '{file_path}': {e}", "path": None}

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict[str, Any]:
        """Edit a file by replacing string occurrences."""
        try:
            resolved_path = self._resolve_path(file_path)
        except ValueError as e:
            return {"error": str(e), "path": None, "occurrences": None}

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

    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[dict[str, Any]] | str:
        """Search for pattern in files."""
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

            # Check if within allowed root
            try:
                fp.relative_to(self.cwd)
            except ValueError:
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
                    rel_path = str(fp.relative_to(self.cwd))
                    results.setdefault(rel_path, []).append((line_num, line))

        matches: list[dict[str, Any]] = []
        for fpath, items in results.items():
            for line_num, line_text in items:
                matches.append({"path": fpath, "line": int(line_num), "text": line_text})
        return matches

    def glob_info(self, pattern: str, path: str = ".") -> list[dict[str, Any]]:
        """Find files matching a glob pattern."""
        if pattern.startswith("/"):
            pattern = pattern.lstrip("/")

        try:
            search_path = self._resolve_path(path)
        except ValueError:
            return []

        if not search_path.exists() or not search_path.is_dir():
            return []

        results: list[dict[str, Any]] = []
        try:
            for matched_path in search_path.rglob(pattern):
                # Check if within allowed root
                try:
                    matched_path.relative_to(self.cwd)
                except ValueError:
                    continue

                try:
                    is_file = matched_path.is_file()
                except OSError:
                    continue
                if not is_file:
                    continue
                rel_path = str(matched_path.relative_to(self.cwd))
                try:
                    st = matched_path.stat()
                    results.append(
                        {
                            "path": rel_path,
                            "is_dir": False,
                            "size": int(st.st_size),
                            "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        }
                    )
                except OSError:
                    results.append({"path": rel_path, "is_dir": False, "size": 0, "modified_at": ""})
        except (OSError, ValueError):
            pass

        results.sort(key=lambda x: x.get("path", ""))
        return results

    def _glob_match(self, name: str, pattern: str) -> bool:
        """Simple glob pattern matching for filenames."""
        import fnmatch

        return fnmatch.fnmatch(name, pattern)


class FastAPIFileServer:
    """FastAPI-based file server with security features."""

    def __init__(
        self,
        root_dir: str | Path | None = None,
        api_key: str | None = None,
        enable_auth: bool = True,
        enable_rate_limit: bool = True,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        """Initialize FastAPI file server.

        Args:
            root_dir: Root directory for file operations
            api_key: API key for authentication (auto-generated if None)
            enable_auth: Enable API key authentication
            enable_rate_limit: Enable rate limiting
            max_requests: Maximum requests per window
            window_seconds: Rate limit window in seconds
        """
        self.root_dir = root_dir
        self.backend = FilesystemBackend(root_dir)
        self.enable_auth = enable_auth
        self.api_key = api_key or self._generate_api_key()
        self.enable_rate_limit = enable_rate_limit
        self.rate_limiter = RateLimiter(max_requests, window_seconds) if enable_rate_limit else None
        self.start_time = time.time()

        self.app = FastAPI(
            title="DeepAgents FileServer",
            description="Secure file server with FastAPI",
            version="2.0.0",
        )

        self._setup_middleware()
        self._setup_routes()

    def _generate_api_key(self) -> str:
        """Generate a secure random API key."""
        return secrets.token_urlsafe(32)

    def _setup_middleware(self):
        """Setup CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _verify_api_key(self, x_api_key: Optional[str] = Header(None)) -> None:
        """Verify API key authentication.

        Args:
            x_api_key: API key from request header

        Raises:
            HTTPException: If authentication fails
        """
        if not self.enable_auth:
            return

        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key. Provide X-API-Key header.",
            )

        if x_api_key != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )

    def _check_rate_limit(self, request: Request) -> None:
        """Check rate limit for the request.

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: If rate limit exceeded
        """
        if not self.enable_rate_limit or not self.rate_limiter:
            return

        client_id = request.client.host if request.client else "unknown"
        if not self.rate_limiter.is_allowed(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(status="ok", uptime=time.time() - self.start_time)

        @self.app.get("/api/ls", response_model=LsResponse, dependencies=[])
        async def list_directory(
            request: Request,
            path: str = ".",
            x_api_key: Optional[str] = Header(None),
        ):
            """List directory contents."""
            self._verify_api_key(x_api_key)
            self._check_rate_limit(request)

            files = self.backend.ls_info(path)
            return LsResponse(files=[FileInfo(**f) for f in files])

        @self.app.get("/api/read", response_model=ReadResponse)
        async def read_file(
            request: Request,
            file_path: str,
            offset: int = 0,
            limit: int = 2000,
            x_api_key: Optional[str] = Header(None),
        ):
            """Read file content with line numbers."""
            self._verify_api_key(x_api_key)
            self._check_rate_limit(request)

            content = self.backend.read(file_path, offset, limit)
            return ReadResponse(content=content)

        @self.app.post("/api/write", response_model=WriteResponse)
        async def write_file(
            request: Request,
            write_request: WriteRequest,
            x_api_key: Optional[str] = Header(None),
        ):
            """Create a new file."""
            self._verify_api_key(x_api_key)
            self._check_rate_limit(request)

            result = self.backend.write(write_request.file_path, write_request.content)
            if result.get("error"):
                raise HTTPException(status_code=400, detail=result["error"])
            return WriteResponse(**result)

        @self.app.post("/api/edit", response_model=EditResponse)
        async def edit_file(
            request: Request,
            edit_request: EditRequest,
            x_api_key: Optional[str] = Header(None),
        ):
            """Edit a file by replacing strings."""
            self._verify_api_key(x_api_key)
            self._check_rate_limit(request)

            result = self.backend.edit(
                edit_request.file_path,
                edit_request.old_string,
                edit_request.new_string,
                edit_request.replace_all,
            )
            if result.get("error"):
                raise HTTPException(status_code=400, detail=result["error"])
            return EditResponse(**result)

        @self.app.get("/api/grep", response_model=GrepResponse)
        async def grep_files(
            request: Request,
            pattern: str,
            path: Optional[str] = None,
            glob: Optional[str] = None,
            x_api_key: Optional[str] = Header(None),
        ):
            """Search for patterns in files."""
            self._verify_api_key(x_api_key)
            self._check_rate_limit(request)

            result = self.backend.grep_raw(pattern, path, glob)
            if isinstance(result, str):
                raise HTTPException(status_code=400, detail=result)
            return GrepResponse(matches=[GrepMatch(**m) for m in result])

        @self.app.get("/api/glob", response_model=GlobResponse)
        async def glob_files(
            request: Request,
            pattern: str,
            path: str = ".",
            x_api_key: Optional[str] = Header(None),
        ):
            """Find files matching glob pattern."""
            self._verify_api_key(x_api_key)
            self._check_rate_limit(request)

            files = self.backend.glob_info(pattern, path)
            return GlobResponse(files=[FileInfo(**f) for f in files])

    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the FastAPI server.

        Args:
            host: Server host
            port: Server port
        """
        print("=" * 80)
        print(f"DeepAgents FastAPI FileServer v2.0.0")
        print("=" * 80)
        print(f"Root directory: {self.backend.cwd}")
        print(f"Server: http://{host}:{port}")
        print(f"Authentication: {'Enabled' if self.enable_auth else 'Disabled'}")
        if self.enable_auth:
            print(f"API Key: {self.api_key}")
            print(f"Header: X-API-Key: {self.api_key}")
        print(f"Rate Limiting: {'Enabled' if self.enable_rate_limit else 'Disabled'}")
        if self.enable_rate_limit and self.rate_limiter:
            print(f"Rate Limit: {self.rate_limiter.max_requests} requests per {self.rate_limiter.window_seconds}s")
        print("\nEndpoints:")
        print("  GET  /health              - Health check")
        print("  GET  /api/ls              - List directory")
        print("  GET  /api/read            - Read file")
        print("  POST /api/write           - Write file")
        print("  POST /api/edit            - Edit file")
        print("  GET  /api/grep            - Search files")
        print("  GET  /api/glob            - Glob pattern matching")
        print("\nDocs: http://{}:{}/docs".format(host, port))
        print("=" * 80)

        uvicorn.run(self.app, host=host, port=port, log_level="info")


def main():
    """Main entry point."""
    import sys

    root_dir = sys.argv[1] if len(sys.argv) > 1 else None
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    api_key = os.environ.get("FILESERVER_API_KEY")

    server = FastAPIFileServer(
        root_dir=root_dir,
        api_key=api_key,
        enable_auth=True,
        enable_rate_limit=True,
    )
    server.run(port=port)


if __name__ == "__main__":
    main()
