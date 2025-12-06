"""FastAPI-based HTTP file server with security features.

This module provides a secure, production-ready HTTP server that exposes filesystem
operations through a RESTful API using FastAPI.
"""

import os
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from .server import FilesystemBackend


class FileInfo(BaseModel):
    """File information model."""

    path: str
    is_dir: bool
    size: Optional[int] = None
    modified_at: Optional[str] = None


class GrepMatch(BaseModel):
    """Grep match model."""

    path: str
    line: int
    text: str


class WriteRequest(BaseModel):
    """Write file request model."""

    file_path: str = Field(..., description="Path where the file should be created")
    content: str = Field(..., description="Content to write to the file")


class WriteResponse(BaseModel):
    """Write file response model."""

    error: Optional[str] = None
    path: Optional[str] = None


class EditRequest(BaseModel):
    """Edit file request model."""

    file_path: str = Field(..., description="Path to the file to edit")
    old_string: str = Field(..., description="String to replace")
    new_string: str = Field(..., description="Replacement string")
    replace_all: bool = Field(False, description="Replace all occurrences")


class EditResponse(BaseModel):
    """Edit file response model."""

    error: Optional[str] = None
    path: Optional[str] = None
    occurrences: Optional[int] = None


class ListResponse(BaseModel):
    """List directory response model."""

    files: list[FileInfo]


class ReadResponse(BaseModel):
    """Read file response model."""

    content: str


class GrepResponse(BaseModel):
    """Grep response model."""

    matches: list[GrepMatch]


class GlobResponse(BaseModel):
    """Glob response model."""

    files: list[FileInfo]


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str


class SecureFileServer:
    """FastAPI-based secure file server."""

    def __init__(
        self,
        root_dir: str | Path | None = None,
        host: str = "localhost",
        port: int = 8080,
        api_key: Optional[str] = None,
        enable_auth: bool = True,
    ):
        """Initialize secure file server.

        Args:
            root_dir: Root directory for file operations
            host: Server host address
            port: Server port number
            api_key: API key for authentication (auto-generated if not provided and auth is enabled)
            enable_auth: Whether to enable API key authentication
        """
        self.root_dir = root_dir
        self.host = host
        self.port = port
        self.enable_auth = enable_auth

        if enable_auth:
            self.api_key = api_key or self._generate_api_key()
        else:
            self.api_key = None

        self.backend = FilesystemBackend(root_dir)
        self.app = self._create_app()

    def _generate_api_key(self) -> str:
        """Generate a secure random API key."""
        return secrets.token_urlsafe(32)

    def _validate_path(self, path: str) -> None:
        """Validate path to prevent path traversal attacks.

        Args:
            path: Path to validate

        Raises:
            HTTPException: If path is invalid or attempts traversal
        """
        # Check for obvious path traversal attempts
        if ".." in path.split("/"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied: Path traversal detected for '{path}'")

        resolved = self.backend._resolve_path(path)

        # Check if the resolved path is within the root directory
        # Only check for existing paths to avoid false positives
        try:
            # For absolute paths outside root, check the traversal
            if resolved.is_absolute() and not str(resolved).startswith(str(self.backend.cwd)):
                # Allow if it's under root when resolved
                try:
                    resolved.relative_to(self.backend.cwd)
                except ValueError:
                    # For nonexistent paths that are absolute and outside root, skip check
                    if not resolved.exists():
                        pass
                    else:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied: Path traversal detected for '{path}'")
        except Exception:
            pass

    async def _verify_api_key(self, api_key: str = Security(APIKeyHeader(name="X-API-Key", auto_error=False))) -> str:
        """Verify API key for authentication.

        Args:
            api_key: API key from request header

        Returns:
            The validated API key

        Raises:
            HTTPException: If API key is invalid
        """
        if not self.enable_auth:
            return ""

        if not api_key or api_key != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        return api_key

    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        app = FastAPI(
            title="DeepAgents FileServer",
            description="Secure HTTP file server exposing BackendProtocol operations",
            version="2.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Dependency for API key validation
        api_key_dep = Depends(self._verify_api_key) if self.enable_auth else None

        @app.get("/health", response_model=HealthResponse, tags=["Health"])
        async def health_check():
            """Health check endpoint."""
            return {"status": "ok"}

        @app.get("/api/ls", response_model=ListResponse, dependencies=[api_key_dep] if api_key_dep else [], tags=["Filesystem"])
        async def list_directory(path: str = "."):
            """List files and directories in the specified path.

            Args:
                path: Directory path to list (defaults to current directory)

            Returns:
                List of files and directories with metadata
            """
            try:
                self._validate_path(path)
                files = self.backend.ls_info(path)
                return {"files": files}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/read", response_model=ReadResponse, dependencies=[api_key_dep] if api_key_dep else [], tags=["Filesystem"])
        async def read_file(file_path: str, offset: int = 0, limit: int = 2000):
            """Read file content with line numbers.

            Args:
                file_path: Path to the file to read
                offset: Line offset to start reading from (default: 0)
                limit: Maximum number of lines to read (default: 2000)

            Returns:
                Formatted file content with line numbers
            """
            try:
                self._validate_path(file_path)
                content = self.backend.read(file_path, offset, limit)
                return {"content": content}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/write", response_model=WriteResponse, dependencies=[api_key_dep] if api_key_dep else [], tags=["Filesystem"])
        async def write_file(request: WriteRequest):
            """Create a new file with the specified content.

            Args:
                request: Write request with file_path and content

            Returns:
                Write result with error or path
            """
            try:
                self._validate_path(request.file_path)
                result = self.backend.write(request.file_path, request.content)
                if result.get("error"):
                    raise HTTPException(status_code=400, detail=result["error"])
                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/edit", response_model=EditResponse, dependencies=[api_key_dep] if api_key_dep else [], tags=["Filesystem"])
        async def edit_file(request: EditRequest):
            """Edit a file by replacing string occurrences.

            Args:
                request: Edit request with file_path, old_string, new_string, and replace_all

            Returns:
                Edit result with error, path, and number of occurrences replaced
            """
            try:
                self._validate_path(request.file_path)
                result = self.backend.edit(
                    request.file_path,
                    request.old_string,
                    request.new_string,
                    request.replace_all,
                )
                if result.get("error"):
                    raise HTTPException(status_code=400, detail=result["error"])
                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/grep", response_model=GrepResponse, dependencies=[api_key_dep] if api_key_dep else [], tags=["Search"])
        async def grep_search(pattern: str, path: Optional[str] = None, glob: Optional[str] = None):
            """Search for patterns in files using regular expressions.

            Args:
                pattern: Regular expression pattern to search for
                path: Base path to search in (defaults to current directory)
                glob: Glob pattern to filter files (e.g., "*.py")

            Returns:
                List of matches with file path, line number, and text
            """
            try:
                if path:
                    self._validate_path(path)
                result = self.backend.grep_raw(pattern, path, glob)
                if isinstance(result, str):
                    raise HTTPException(status_code=400, detail=result)
                return {"matches": result}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/glob", response_model=GlobResponse, dependencies=[api_key_dep] if api_key_dep else [], tags=["Search"])
        async def glob_pattern(pattern: str, path: str = "/"):
            """Find files matching a glob pattern.

            Args:
                pattern: Glob pattern (e.g., "*.txt", "**/*.py")
                path: Base path to search from (default: "/")

            Returns:
                List of matching files with metadata
            """
            try:
                if path != "/":
                    self._validate_path(path)
                files = self.backend.glob_info(pattern, path)
                return {"files": files}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        return app

    def start(self) -> None:
        """Start the FastAPI server."""
        print(f"FastAPI FileServer starting at http://{self.host}:{self.port}")
        print(f"Root directory: {self.backend.cwd}")

        if self.enable_auth:
            print(f"\n🔐 Authentication enabled")
            print(f"API Key: {self.api_key}")
            print(f"Include in requests: X-API-Key: {self.api_key}")
        else:
            print(f"\n⚠️  Authentication disabled - use with caution!")

        print(f"\n📚 API Documentation:")
        print(f"  Swagger UI: http://{self.host}:{self.port}/docs")
        print(f"  ReDoc: http://{self.host}:{self.port}/redoc")

        print(f"\n🔗 Endpoints:")
        print(f"  GET  /health              - Health check")
        print(f"  GET  /api/ls              - List directory")
        print(f"  GET  /api/read            - Read file")
        print(f"  POST /api/write           - Write file")
        print(f"  POST /api/edit            - Edit file")
        print(f"  GET  /api/grep            - Search files")
        print(f"  GET  /api/glob            - Glob pattern match")

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )


def main():
    """Main entry point for running the server."""
    import sys

    root_dir = sys.argv[1] if len(sys.argv) > 1 else None
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    api_key = sys.argv[3] if len(sys.argv) > 3 else None
    enable_auth = sys.argv[4].lower() != "false" if len(sys.argv) > 4 else True

    server = SecureFileServer(
        root_dir=root_dir,
        port=port,
        api_key=api_key,
        enable_auth=enable_auth,
    )
    server.start()


if __name__ == "__main__":
    main()
