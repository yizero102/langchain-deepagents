"""FastAPI-based file server with enhanced security features.

This module provides a secure HTTP server that exposes filesystem operations
through a RESTful API using FastAPI with authentication and rate limiting.
"""

import os
import re
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
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
    """Write operation request."""

    file_path: str = Field(..., description="Path where the file should be created")
    content: str = Field(..., description="Content to write to the file")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path to prevent path traversal."""
        if ".." in v or v.startswith("/.."):
            raise ValueError("Path traversal detected")
        return v


class EditRequest(BaseModel):
    """Edit operation request."""

    file_path: str = Field(..., description="Path to the file to edit")
    old_string: str = Field(..., description="String to replace")
    new_string: str = Field(default="", description="Replacement string")
    replace_all: bool = Field(default=False, description="Replace all occurrences")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path to prevent path traversal."""
        if ".." in v or v.startswith("/.."):
            raise ValueError("Path traversal detected")
        return v


class WriteResponse(BaseModel):
    """Write operation response."""

    error: str | None = None
    path: str | None = None


class EditResponse(BaseModel):
    """Edit operation response."""

    error: str | None = None
    path: str | None = None
    occurrences: int | None = None


class ReadResponse(BaseModel):
    """Read operation response."""

    content: str


class ListResponse(BaseModel):
    """List operation response."""

    files: list[FileInfo]


class GrepResponse(BaseModel):
    """Grep operation response."""

    matches: list[GrepMatch]


class GlobResponse(BaseModel):
    """Glob operation response."""

    files: list[FileInfo]


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["ok"] = "ok"


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}

    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit.

        Args:
            client_id: Client identifier (IP address or API key)

        Returns:
            True if within rate limit, False if exceeded
        """
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []

        # Remove old requests outside the window
        self.requests[client_id] = [req_time for req_time in self.requests[client_id] if now - req_time < self.window_seconds]

        # Check if limit exceeded
        if len(self.requests[client_id]) >= self.max_requests:
            return False

        # Add current request
        self.requests[client_id].append(now)
        return True


class FilesystemBackend:
    """Minimal filesystem backend implementation."""

    def __init__(self, root_dir: str | Path | None = None, max_file_size_mb: int = 10) -> None:
        """Initialize filesystem backend.

        Args:
            root_dir: Root directory for file operations
            max_file_size_mb: Maximum file size in MB for grep operations
        """
        self.cwd = Path(root_dir).resolve() if root_dir else Path.cwd()
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def _resolve_path(self, key: str) -> Path:
        """Resolve a file path relative to root directory.

        Args:
            key: File path (absolute or relative)

        Returns:
            Resolved absolute Path object

        Raises:
            ValueError: If path traversal is detected
        """
        # Prevent path traversal
        if ".." in key or key.startswith("/.."):
            raise ValueError("Path traversal detected")

        path = Path(key)
        if path.is_absolute():
            resolved = path
        else:
            resolved = (self.cwd / path).resolve()

        # Ensure resolved path is within root directory
        try:
            resolved.relative_to(self.cwd)
        except ValueError:
            raise ValueError("Path traversal detected: path is outside root directory")

        return resolved

    def ls_info(self, path: str) -> list[FileInfo]:
        """List files and directories in the specified directory.

        Args:
            path: Directory path to list files from

        Returns:
            List of FileInfo objects for files and directories
        """
        try:
            dir_path = self._resolve_path(path)
        except ValueError:
            return []

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
                            FileInfo(
                                path=abs_path,
                                is_dir=False,
                                size=int(st.st_size),
                                modified_at=datetime.fromtimestamp(st.st_mtime).isoformat(),
                            )
                        )
                    except OSError:
                        results.append(FileInfo(path=abs_path, is_dir=False))
                elif is_dir:
                    try:
                        st = child_path.stat()
                        results.append(
                            FileInfo(
                                path=abs_path + "/",
                                is_dir=True,
                                size=0,
                                modified_at=datetime.fromtimestamp(st.st_mtime).isoformat(),
                            )
                        )
                    except OSError:
                        results.append(FileInfo(path=abs_path + "/", is_dir=True))
        except (OSError, PermissionError):
            pass

        results.sort(key=lambda x: x.path)
        return results

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file content with line numbers.

        Args:
            file_path: File path to read
            offset: Line offset to start reading from (0-indexed)
            limit: Maximum number of lines to read

        Returns:
            Formatted file content with line numbers, or error message
        """
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

    def write(self, file_path: str, content: str) -> WriteResponse:
        """Create a new file with content.

        Args:
            file_path: Path to create the file
            content: File content

        Returns:
            WriteResponse with error or path
        """
        try:
            resolved_path = self._resolve_path(file_path)
        except ValueError as e:
            return WriteResponse(error=str(e), path=None)

        if resolved_path.exists():
            return WriteResponse(
                error=f"Cannot write to {file_path} because it already exists. Read and then make an edit, or write to a new path.",
                path=None,
            )

        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)
            return WriteResponse(error=None, path=file_path)
        except (OSError, UnicodeEncodeError) as e:
            return WriteResponse(error=f"Error writing file '{file_path}': {e}", path=None)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResponse:
        """Edit a file by replacing string occurrences.

        Args:
            file_path: Path to the file to edit
            old_string: String to replace
            new_string: Replacement string
            replace_all: If True, replace all occurrences; otherwise replace only first

        Returns:
            EditResponse with error, path, and number of occurrences replaced
        """
        try:
            resolved_path = self._resolve_path(file_path)
        except ValueError as e:
            return EditResponse(error=str(e), path=None, occurrences=None)

        if not resolved_path.exists() or not resolved_path.is_file():
            return EditResponse(error=f"Error: File '{file_path}' not found", path=None, occurrences=None)

        try:
            with open(resolved_path, encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return EditResponse(
                    error=f"String '{old_string[:50]}...' not found in file",
                    path=None,
                    occurrences=None,
                )

            if replace_all:
                new_content = content.replace(old_string, new_string)
                occurrences = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                occurrences = 1

            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return EditResponse(error=None, path=file_path, occurrences=occurrences)
        except (OSError, UnicodeDecodeError, UnicodeEncodeError) as e:
            return EditResponse(error=f"Error editing file '{file_path}': {e}", path=None, occurrences=None)

    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[GrepMatch] | str:
        """Search for pattern in files.

        Args:
            pattern: Regular expression pattern to search for
            path: Base path to search in (defaults to current directory)
            glob: Glob pattern to filter files (e.g., "*.py")

        Returns:
            List of GrepMatch objects or error string
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
                matches.append(GrepMatch(path=fpath, line=int(line_num), text=line_text))
        return matches

    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.py", "**/*.txt")
            path: Base path to search from

        Returns:
            List of FileInfo objects for matching files
        """
        if pattern.startswith("/"):
            pattern = pattern.lstrip("/")

        try:
            search_path = self.cwd if path == "/" else self._resolve_path(path)
        except ValueError:
            return []

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
                        FileInfo(
                            path=abs_path,
                            is_dir=False,
                            size=int(st.st_size),
                            modified_at=datetime.fromtimestamp(st.st_mtime).isoformat(),
                        )
                    )
                except OSError:
                    results.append(FileInfo(path=abs_path, is_dir=False))
        except (OSError, ValueError):
            pass

        results.sort(key=lambda x: x.path)
        return results

    def _glob_match(self, name: str, pattern: str) -> bool:
        """Simple glob pattern matching for filenames."""
        import fnmatch

        return fnmatch.fnmatch(name, pattern)


def create_app(
    root_dir: str | Path | None = None,
    api_key: str | None = None,
    enable_rate_limiting: bool = True,
    rate_limit_requests: int = 100,
    rate_limit_window: int = 60,
) -> FastAPI:
    """Create FastAPI application with security features.

    Args:
        root_dir: Root directory for file operations
        api_key: API key for authentication (generated if not provided)
        enable_rate_limiting: Whether to enable rate limiting
        rate_limit_requests: Maximum requests per window
        rate_limit_window: Time window in seconds

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="DeepAgents FileServer",
        description="Secure HTTP file server exposing BackendProtocol operations",
        version="0.2.0",
    )

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize backend
    backend = FilesystemBackend(root_dir)

    # Generate API key if not provided
    if api_key is None:
        api_key = secrets.token_urlsafe(32)
        print(f"Generated API Key: {api_key}")
        print("Include this key in the 'X-API-Key' header for authenticated requests")

    # Initialize rate limiter
    rate_limiter = RateLimiter(max_requests=rate_limit_requests, window_seconds=rate_limit_window)

    async def verify_api_key(x_api_key: str = Header(None)) -> str:
        """Verify API key from request header.

        Args:
            x_api_key: API key from X-API-Key header

        Returns:
            Verified API key

        Raises:
            HTTPException: If API key is missing or invalid
        """
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key. Include 'X-API-Key' header",
            )
        if x_api_key != api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return x_api_key

    async def check_rate_limit(request: Request, api_key_value: str = Depends(verify_api_key)) -> None:
        """Check rate limit for the request.

        Args:
            request: HTTP request
            api_key_value: Verified API key

        Raises:
            HTTPException: If rate limit is exceeded
        """
        if not enable_rate_limiting:
            return

        client_id = api_key_value or request.client.host
        if not rate_limiter.check_rate_limit(client_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {rate_limit_requests} requests per {rate_limit_window} seconds",
            )

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(status="ok")

    @app.get("/api/ls", response_model=ListResponse, dependencies=[Depends(check_rate_limit)], tags=["Filesystem"])
    async def list_directory(path: str = Query(default=".", description="Directory path to list")):
        """List files and directories in the specified path."""
        try:
            files = backend.ls_info(path)
            return ListResponse(files=files)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    @app.get("/api/read", response_model=ReadResponse, dependencies=[Depends(check_rate_limit)], tags=["Filesystem"])
    async def read_file(
        file_path: str = Query(..., description="Path to the file to read"),
        offset: int = Query(default=0, description="Line offset to start reading from"),
        limit: int = Query(default=2000, description="Maximum number of lines to read"),
    ):
        """Read file content with line numbers."""
        try:
            content = backend.read(file_path, offset, limit)
            return ReadResponse(content=content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    @app.post("/api/write", response_model=WriteResponse, dependencies=[Depends(check_rate_limit)], tags=["Filesystem"])
    async def write_file(request: WriteRequest):
        """Create a new file with content."""
        try:
            result = backend.write(request.file_path, request.content)
            if result.error:
                raise HTTPException(status_code=400, detail=result.error)
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    @app.post("/api/edit", response_model=EditResponse, dependencies=[Depends(check_rate_limit)], tags=["Filesystem"])
    async def edit_file(request: EditRequest):
        """Edit a file by replacing string occurrences."""
        try:
            result = backend.edit(request.file_path, request.old_string, request.new_string, request.replace_all)
            if result.error:
                raise HTTPException(status_code=400, detail=result.error)
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    @app.get("/api/grep", response_model=GrepResponse, dependencies=[Depends(check_rate_limit)], tags=["Search"])
    async def grep_search(
        pattern: str = Query(..., description="Regular expression pattern to search for"),
        path: str = Query(default=None, description="Base path to search in"),
        glob: str = Query(default=None, description="Glob pattern to filter files"),
    ):
        """Search for patterns in files using regular expressions."""
        try:
            result = backend.grep_raw(pattern, path, glob)
            if isinstance(result, str):
                raise HTTPException(status_code=400, detail=result)
            return GrepResponse(matches=result)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    @app.get("/api/glob", response_model=GlobResponse, dependencies=[Depends(check_rate_limit)], tags=["Search"])
    async def glob_pattern(
        pattern: str = Query(..., description="Glob pattern (e.g., '*.txt', '**/*.py')"),
        path: str = Query(default="/", description="Base path to search from"),
    ):
        """Find files matching a glob pattern."""
        try:
            files = backend.glob_info(pattern, path)
            return GlobResponse(files=files)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    return app


class FastAPIFileServer:
    """FastAPI-based file server with security features."""

    def __init__(
        self,
        root_dir: str | Path | None = None,
        host: str = "localhost",
        port: int = 8080,
        api_key: str | None = None,
        enable_rate_limiting: bool = True,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60,
    ) -> None:
        """Initialize FastAPI file server.

        Args:
            root_dir: Root directory for file operations
            host: Server host address
            port: Server port number
            api_key: API key for authentication
            enable_rate_limiting: Whether to enable rate limiting
            rate_limit_requests: Maximum requests per window
            rate_limit_window: Time window in seconds
        """
        self.root_dir = root_dir
        self.host = host
        self.port = port
        self.api_key = api_key
        self.app = create_app(
            root_dir=root_dir,
            api_key=api_key,
            enable_rate_limiting=enable_rate_limiting,
            rate_limit_requests=rate_limit_requests,
            rate_limit_window=rate_limit_window,
        )

    def start(self) -> None:
        """Start the FastAPI server."""
        print(f"FastAPI FileServer starting at http://{self.host}:{self.port}")
        print(f"Root directory: {Path(self.root_dir).resolve() if self.root_dir else Path.cwd()}")
        print("\nSecurity features enabled:")
        print("  - API Key Authentication")
        print("  - Rate Limiting")
        print("  - Path Traversal Prevention")
        print("\nAPI Documentation: http://{self.host}:{self.port}/docs")
        print()
        uvicorn.run(self.app, host=self.host, port=self.port)


if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else None
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

    server = FastAPIFileServer(root_dir=root, port=port)
    server.start()
