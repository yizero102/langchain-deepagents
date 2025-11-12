"""DeepAgents FileServer - Independent HTTP file server exposing BackendProtocol operations.

This module provides a standalone HTTP server that exposes filesystem operations
through a RESTful API. It wraps FilesystemBackend operations and makes them
accessible via HTTP endpoints.
"""

from fileserver.server import FileServer

__all__ = ["FileServer"]
__version__ = "0.1.0"
