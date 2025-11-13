"""DeepAgents FileServer - Independent HTTP file server exposing BackendProtocol operations.

This module provides a standalone HTTP server that exposes filesystem operations
through a RESTful API. It wraps FilesystemBackend operations and makes them
accessible via HTTP endpoints.
"""

from fileserver.server import FileServer
from fileserver.server_fastapi import FastAPIFileServer, create_app

__all__ = ["FileServer", "FastAPIFileServer", "create_app"]
__version__ = "0.2.0"
