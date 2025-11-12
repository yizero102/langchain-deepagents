# FastAPI FileServer Improvements

## Overview

The FileServer has been significantly enhanced with a new FastAPI-based implementation that includes comprehensive security features, better performance, and improved API design.

## New Features

### 1. FastAPI Implementation (`fastapi_server.py`)

The new `FastAPIFileServer` replaces the basic http.server implementation with a production-ready FastAPI application.

#### Key Improvements:

- **Modern Framework**: Built on FastAPI for better performance and features
- **Automatic API Documentation**: Interactive API docs at `/docs` endpoint
- **Request Validation**: Pydantic models ensure data integrity
- **Better Error Handling**: Structured error responses with proper HTTP status codes
- **Type Safety**: Full type hints and validation

### 2. Security Features

#### API Key Authentication

- **Configurable Authentication**: Can be enabled/disabled via configuration
- **API Key Header**: Authentication via `X-API-Key` header
- **Auto-generated Keys**: Secure random API keys generated if not provided
- **Environment Variable Support**: Can set API key via `FILESERVER_API_KEY` env var

```python
from fileserver import FastAPIFileServer

# With authentication
server = FastAPIFileServer(
    root_dir="/data",
    api_key="your-secure-key",
    enable_auth=True
)

# Without authentication (development only)
server = FastAPIFileServer(
    root_dir="/data",
    enable_auth=False
)
```

#### Rate Limiting

- **Configurable Limits**: Set max requests per time window
- **Per-Client Tracking**: Limits enforced per IP address
- **Automatic Cleanup**: Old request records automatically cleaned up
- **Customizable Windows**: Configure both request count and time window

```python
server = FastAPIFileServer(
    root_dir="/data",
    enable_rate_limit=True,
    max_requests=100,  # 100 requests
    window_seconds=60   # per 60 seconds
)
```

#### Path Traversal Protection

- **Input Validation**: Pydantic validators reject path traversal attempts
- **Backend Protection**: FilesystemBackend validates all resolved paths
- **Absolute Path Blocking**: Rejects absolute paths in requests
- **Double-dot Prevention**: Blocks `..` in file paths

Examples of blocked requests:
```bash
# These will be rejected with 422 Validation Error:
POST /api/write {"file_path": "../../../etc/passwd", "content": "..."}
POST /api/write {"file_path": "/etc/passwd", "content": "..."}
```

### 3. Enhanced API Design

#### Request/Response Models

All endpoints use Pydantic models for validation:

- `WriteRequest`/`WriteResponse`
- `EditRequest`/`EditResponse`
- `ReadResponse`
- `LsResponse`
- `GrepResponse`
- `GlobResponse`
- `HealthResponse`

#### CORS Support

Full CORS middleware enabled for web application access:

```python
# Configured automatically in FastAPIFileServer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Usage Examples

#### Starting the Server

```bash
# With default settings
python -m fileserver.fastapi_server

# With custom directory and port
python -m fileserver.fastapi_server /path/to/root 9000

# With environment variable for API key
export FILESERVER_API_KEY="my-secure-key-12345"
python -m fileserver.fastapi_server
```

#### Python API

```python
from fileserver import FastAPIFileServer

server = FastAPIFileServer(
    root_dir="/data",
    api_key="secure-api-key",
    enable_auth=True,
    enable_rate_limit=True,
    max_requests=100,
    window_seconds=60
)

server.run(host="0.0.0.0", port=8080)
```

When the server starts, it displays:

```
================================================================================
DeepAgents FastAPI FileServer v2.0.0
================================================================================
Root directory: /data
Server: http://0.0.0.0:8080
Authentication: Enabled
API Key: secure-api-key
Header: X-API-Key: secure-api-key
Rate Limiting: Enabled
Rate Limit: 100 requests per 60s

Endpoints:
  GET  /health              - Health check
  GET  /api/ls              - List directory
  GET  /api/read            - Read file
  POST /api/write           - Write file
  POST /api/edit            - Edit file
  GET  /api/grep            - Search files
  GET  /api/glob            - Glob pattern matching

Docs: http://0.0.0.0:8080/docs
================================================================================
```

#### Making Authenticated Requests

```bash
# With API key
curl -H "X-API-Key: secure-api-key" http://localhost:8080/api/ls

# Python requests
import requests

headers = {"X-API-Key": "secure-api-key"}
response = requests.get("http://localhost:8080/api/ls", headers=headers)
```

### 5. Testing

Comprehensive test suite added in `tests/test_fastapi_server.py`:

- ✅ 32 tests total
- ✅ Authentication tests (valid/invalid/missing keys)
- ✅ Rate limiting enforcement tests
- ✅ Path traversal security tests
- ✅ All CRUD operations (write, read, edit, ls, grep, glob)
- ✅ Unicode content handling
- ✅ Error handling and edge cases
- ✅ Concurrent operations

Run tests:
```bash
cd libs/deepagents-fileserver
pytest tests/test_fastapi_server.py -v
```

### 6. Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: Available at `http://localhost:8080/docs`
- **ReDoc**: Available at `http://localhost:8080/redoc`
- **OpenAPI Schema**: Available at `http://localhost:8080/openapi.json`

These docs allow you to:
- Browse all available endpoints
- See request/response schemas
- Try out API calls directly in the browser
- View authentication requirements

### 7. Comparison: Original vs FastAPI

| Feature | Original (http.server) | FastAPI Implementation |
|---------|----------------------|----------------------|
| Framework | stdlib http.server | FastAPI + Uvicorn |
| Authentication | ❌ None | ✅ API Key-based |
| Rate Limiting | ❌ None | ✅ Configurable |
| Path Traversal Protection | ⚠️ Basic | ✅ Multi-layer |
| API Documentation | ❌ Manual | ✅ Auto-generated |
| Request Validation | ⚠️ Manual | ✅ Pydantic models |
| Error Handling | ⚠️ Basic | ✅ Structured responses |
| CORS Support | ⚠️ Manual headers | ✅ Middleware |
| Type Safety | ⚠️ Partial | ✅ Full type hints |
| Performance | Good | Better (async) |
| Test Coverage | 26 tests | 32 tests + security |

### 8. Production Deployment Recommendations

For production use, consider:

1. **Use HTTPS**: Deploy behind a reverse proxy (nginx, Caddy) with TLS
2. **Strong API Keys**: Use long, random API keys (32+ characters)
3. **Rate Limiting**: Enable and tune based on your use case
4. **Network Security**: Restrict access via firewall rules
5. **Monitoring**: Add logging and monitoring for security events
6. **Regular Updates**: Keep FastAPI and dependencies updated

Example nginx configuration:
```nginx
server {
    listen 443 ssl;
    server_name fileserver.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Migration Guide

To migrate from the original server to FastAPI:

1. **Update imports**:
   ```python
   # Old
   from fileserver import FileServer
   
   # New
   from fileserver import FastAPIFileServer
   ```

2. **Update initialization**:
   ```python
   # Old
   server = FileServer(root_dir="/data", port=8080)
   
   # New
   server = FastAPIFileServer(
       root_dir="/data",
       enable_auth=True,
       enable_rate_limit=True
   )
   server.run(port=8080)
   ```

3. **Update client code** to include API key:
   ```python
   # Add X-API-Key header to all requests
   headers = {"X-API-Key": "your-api-key"}
   response = requests.get(url, headers=headers)
   ```

## Conclusion

The FastAPI implementation provides a production-ready, secure file server with modern features while maintaining backward compatibility with the existing API endpoints. The addition of authentication, rate limiting, and enhanced security makes it suitable for real-world deployments.
