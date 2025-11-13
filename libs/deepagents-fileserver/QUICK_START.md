# FileServer Quick Start Guide

## Installation

```bash
cd libs/deepagents-fileserver
pip install -e .
```

## Start Server

### Option 1: Command Line
```bash
# Default: current directory, port 8080
python -m fileserver.server

# Custom directory
python -m fileserver.server /path/to/files

# Custom directory and port
python -m fileserver.server /path/to/files 9000
```

### Option 2: Python API
```python
from fileserver import FileServer

server = FileServer(root_dir="/path/to/files", port=8080)
server.start()  # Blocks until Ctrl+C
```

## API Examples

### Health Check
```bash
curl http://localhost:8080/health
```

### Write a File
```bash
curl -X POST http://localhost:8080/api/write \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test.txt", "content": "Hello World"}'
```

### Read a File
```bash
curl "http://localhost:8080/api/read?file_path=test.txt"
```

### Edit a File
```bash
curl -X POST http://localhost:8080/api/edit \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test.txt", "old_string": "World", "new_string": "Python"}'
```

### List Directory
```bash
curl "http://localhost:8080/api/ls?path=."
```

### Search Files (Grep)
```bash
curl "http://localhost:8080/api/grep?pattern=TODO&path=."
```

### Find Files (Glob)
```bash
curl "http://localhost:8080/api/glob?pattern=*.py&path=."
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run integration test
python integration_test.py

# Run demo
python demo_fileserver.py

# Run comprehensive verification
./verify_all.sh
```

## Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/ls?path=<path>` | List directory |
| GET | `/api/read?file_path=<path>&offset=<n>&limit=<n>` | Read file |
| POST | `/api/write` | Create file |
| POST | `/api/edit` | Edit file |
| GET | `/api/grep?pattern=<regex>&path=<path>&glob=<pattern>` | Search |
| GET | `/api/glob?pattern=<glob>&path=<path>` | Find files |

## Python Usage

```python
import requests

BASE_URL = "http://localhost:8080"

# Write file
requests.post(f"{BASE_URL}/api/write", 
    json={"file_path": "test.txt", "content": "Hello"})

# Read file
response = requests.get(f"{BASE_URL}/api/read?file_path=test.txt")
print(response.json()["content"])

# Edit file
requests.post(f"{BASE_URL}/api/edit",
    json={"file_path": "test.txt", "old_string": "Hello", "new_string": "Hi"})

# Search
response = requests.get(f"{BASE_URL}/api/grep?pattern=TODO")
print(response.json()["matches"])
```

## Features

✅ Zero external dependencies (Python standard library only)
✅ All BackendProtocol operations via HTTP
✅ JSON request/response format
✅ CORS enabled
✅ Unicode/emoji support
✅ Comprehensive error handling
✅ 26 test cases (100% passing)

For complete documentation, see [README.md](README.md)
