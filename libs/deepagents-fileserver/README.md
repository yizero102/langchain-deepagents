# DeepAgents FileServer

An independent HTTP file server that exposes BackendProtocol operations through RESTful APIs.

## 🐳 Docker Support

The FileServer is fully containerized and ready for Docker deployment. See [DOCKER.md](DOCKER.md) for complete documentation.

**Quick Start with Docker:**
```bash
# Using docker-compose (recommended)
docker-compose up -d

# Using Docker CLI
docker build -t deepagents-fileserver .
docker run -d -p 8080:8080 -v $(pwd)/data:/data deepagents-fileserver
```

## Features

### Standard Server (http.server)
- **Zero Dependencies**: Uses only Python standard library (no external dependencies)
- **RESTful API**: All filesystem operations available via HTTP endpoints
- **Full BackendProtocol Support**: Implements all operations from the DeepAgents BackendProtocol
- **CORS Enabled**: Can be accessed from web applications
- **Standalone**: Can run independently without DeepAgents installation

### FastAPI Server (Recommended for Production) 🆕
- **API Key Authentication**: Secure endpoints with configurable API keys
- **Rate Limiting**: Built-in rate limiting to prevent abuse
- **Path Traversal Prevention**: Automatic validation prevents directory traversal attacks
- **Input Validation**: Pydantic models ensure all inputs are validated
- **OpenAPI Documentation**: Interactive API docs at `/docs` endpoint
- **Production Ready**: Built on FastAPI and Uvicorn for high performance

## Installation

```bash
# From the project root
pip install libs/deepagents-fileserver
```

## Quick Start

### Option 1: FastAPI Server (Recommended) 🆕

**Running from Command Line:**
```bash
# Run with auto-generated API key
python -m fileserver.server_fastapi

# Run with custom root directory
python -m fileserver.server_fastapi /path/to/root

# Run with custom root directory and port
python -m fileserver.server_fastapi /path/to/root 9000
```

**Python API:**
```python
from fileserver import FastAPIFileServer

# Create and start server with security features
server = FastAPIFileServer(
    root_dir="/path/to/root",
    host="localhost",
    port=8080,
    api_key="your-secret-key",  # Or None for auto-generated
    enable_rate_limiting=True,
    rate_limit_requests=100,
    rate_limit_window=60
)
server.start()  # Blocks until Ctrl+C
```

**Key Features:**
- API Key is auto-generated if not provided (printed to console)
- Include API key in `X-API-Key` header for all requests (except `/health`)
- Interactive API documentation available at `http://localhost:8080/docs`
- See [FASTAPI_SECURITY_GUIDE.md](FASTAPI_SECURITY_GUIDE.md) for detailed security documentation

### Option 2: Standard Server (Simple, No Dependencies)

**Running from Command Line:**
```bash
# Run with default settings (current directory, port 8080)
python -m fileserver.server

# Run with custom root directory
python -m fileserver.server /path/to/root

# Run with custom root directory and port
python -m fileserver.server /path/to/root 9000
```

**Python API:**
```python
from fileserver import FileServer

# Create and start server
server = FileServer(root_dir="/path/to/root", host="localhost", port=8080)
server.start()  # Blocks until Ctrl+C
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns server status.

**Response:**
```json
{
  "status": "ok"
}
```

### List Directory

```bash
GET /api/ls?path=/path/to/directory
```

Lists files and directories in the specified path.

**Parameters:**
- `path` (optional): Directory path to list (defaults to current directory)

**Response:**
```json
{
  "files": [
    {
      "path": "/path/to/file.txt",
      "is_dir": false,
      "size": 1234,
      "modified_at": "2024-01-15T10:30:00"
    },
    {
      "path": "/path/to/directory/",
      "is_dir": true,
      "size": 0,
      "modified_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### Read File

```bash
GET /api/read?file_path=/path/to/file.txt&offset=0&limit=2000
```

Reads file content with line numbers.

**Parameters:**
- `file_path` (required): Path to the file to read
- `offset` (optional): Line offset to start reading from (default: 0)
- `limit` (optional): Maximum number of lines to read (default: 2000)

**Response:**
```json
{
  "content": "    1 | Line 1\n    2 | Line 2\n    3 | Line 3"
}
```

### Write File

```bash
POST /api/write
Content-Type: application/json

{
  "file_path": "/path/to/newfile.txt",
  "content": "File content here"
}
```

Creates a new file with the specified content.

**Request Body:**
- `file_path` (required): Path where the file should be created
- `content` (required): Content to write to the file

**Response (Success):**
```json
{
  "error": null,
  "path": "/path/to/newfile.txt"
}
```

**Response (Error):**
```json
{
  "error": "Cannot write to /path/to/newfile.txt because it already exists."
}
```

### Edit File

```bash
POST /api/edit
Content-Type: application/json

{
  "file_path": "/path/to/file.txt",
  "old_string": "old text",
  "new_string": "new text",
  "replace_all": false
}
```

Edits a file by replacing string occurrences.

**Request Body:**
- `file_path` (required): Path to the file to edit
- `old_string` (required): String to replace
- `new_string` (required): Replacement string
- `replace_all` (optional): Replace all occurrences (default: false)

**Response (Success):**
```json
{
  "error": null,
  "path": "/path/to/file.txt",
  "occurrences": 1
}
```

### Grep (Search)

```bash
GET /api/grep?pattern=search_pattern&path=/search/path&glob=*.txt
```

Searches for patterns in files using regular expressions.

**Parameters:**
- `pattern` (required): Regular expression pattern to search for
- `path` (optional): Base path to search in (defaults to current directory)
- `glob` (optional): Glob pattern to filter files (e.g., "*.py")

**Response:**
```json
{
  "matches": [
    {
      "path": "/path/to/file.txt",
      "line": 5,
      "text": "Line containing the search pattern"
    }
  ]
}
```

### Glob (Pattern Matching)

```bash
GET /api/glob?pattern=*.txt&path=/search/path
```

Finds files matching a glob pattern.

**Parameters:**
- `pattern` (required): Glob pattern (e.g., "*.txt", "**/*.py")
- `path` (optional): Base path to search from (default: "/")

**Response:**
```json
{
  "files": [
    {
      "path": "/path/to/file1.txt",
      "is_dir": false,
      "size": 1234,
      "modified_at": "2024-01-15T10:30:00"
    },
    {
      "path": "/path/to/file2.txt",
      "is_dir": false,
      "size": 5678,
      "modified_at": "2024-01-15T11:00:00"
    }
  ]
}
```

## Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install pytest

# Run tests
cd libs/deepagents-fileserver
pytest tests/ -v
```

## Usage Examples

### Using curl

```bash
# Health check
curl http://localhost:8080/health

# List directory
curl "http://localhost:8080/api/ls?path=/tmp"

# Read file
curl "http://localhost:8080/api/read?file_path=/tmp/test.txt"

# Write file
curl -X POST http://localhost:8080/api/write \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/tmp/newfile.txt", "content": "Hello World"}'

# Edit file
curl -X POST http://localhost:8080/api/edit \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/tmp/newfile.txt", "old_string": "World", "new_string": "Python"}'

# Search files
curl "http://localhost:8080/api/grep?pattern=TODO&path=/tmp"

# Glob pattern
curl "http://localhost:8080/api/glob?pattern=*.py&path=/tmp"
```

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8080"

# Write a file
response = requests.post(
    f"{BASE_URL}/api/write",
    json={"file_path": "test.txt", "content": "Hello World"}
)
print(response.json())

# Read the file
response = requests.get(f"{BASE_URL}/api/read?file_path=test.txt")
print(response.json())

# Search for pattern
response = requests.get(f"{BASE_URL}/api/grep?pattern=Hello")
print(response.json())
```

## Architecture

The FileServer module is designed to be completely independent:

- **No DeepAgents Dependencies**: Contains its own minimal implementation of FilesystemBackend
- **Standard Library Only**: Uses only Python's built-in `http.server` module
- **Lightweight**: Minimal overhead, suitable for production use
- **Extensible**: Easy to add new endpoints or customize behavior

## Security Considerations

### FastAPI Server (Recommended for Production)

✅ **Security Features Implemented:**
- **API Key Authentication**: All endpoints (except `/health`) require authentication
- **Rate Limiting**: Configurable rate limiting to prevent abuse
- **Path Traversal Prevention**: Automatic validation prevents directory traversal attacks
- **Input Validation**: Pydantic models validate all request data
- **HTTPS Support**: Can be deployed with TLS/SSL via Uvicorn or reverse proxy

See [FASTAPI_SECURITY_GUIDE.md](FASTAPI_SECURITY_GUIDE.md) for comprehensive security documentation.

### Standard Server

⚠️ **Security Warnings:**
- The standard server does not implement authentication by default
- All file operations are performed with the permissions of the user running the server
- Path traversal attempts are not explicitly prevented (use with caution)
- For production use with the standard server, consider:
  - Adding authentication/authorization at the network level
  - Implementing rate limiting via reverse proxy
  - Running behind a reverse proxy (nginx, Apache)
  - Restricting access to specific IP ranges

**Recommendation:** Use the FastAPI server for production deployments.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please ensure:
- All tests pass: `pytest tests/ -v`
- Code follows Python style guidelines
- New features include corresponding tests
