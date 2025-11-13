# FastAPI FileServer Security Guide

This document describes the security features implemented in the FastAPI-based file server and how to use them effectively.

## Overview

The FastAPI FileServer provides a secure, production-ready HTTP API for filesystem operations with the following security features:

- **API Key Authentication**: Protect endpoints with API key-based authentication
- **Rate Limiting**: Prevent abuse with configurable rate limits
- **Path Traversal Prevention**: Automatic validation prevents directory traversal attacks
- **Input Validation**: Pydantic models ensure all inputs are validated
- **CORS Support**: Configurable CORS for web applications
- **OpenAPI Documentation**: Built-in interactive API documentation

## Security Features

### 1. API Key Authentication

All endpoints (except `/health`) require authentication via the `X-API-Key` header.

#### Auto-Generated API Key

```python
from fileserver import FastAPIFileServer

# Server will generate and print a secure API key
server = FastAPIFileServer(root_dir="/data", port=8080)
server.start()
# Output: Generated API Key: abc123xyz...
```

#### Custom API Key

```python
from fileserver import FastAPIFileServer

server = FastAPIFileServer(
    root_dir="/data",
    port=8080,
    api_key="my-secure-api-key-here"
)
server.start()
```

#### Using the API Key

```bash
# Include the API key in the X-API-Key header
curl -H "X-API-Key: your-api-key-here" http://localhost:8080/api/ls
```

**Authentication Errors:**
- `401 Unauthorized`: Missing or invalid API key
- Header must be named exactly `X-API-Key`

### 2. Rate Limiting

Protect your server from abuse with configurable rate limiting per API key.

#### Default Configuration

```python
# Default: 100 requests per 60 seconds
server = FastAPIFileServer(root_dir="/data")
```

#### Custom Rate Limits

```python
server = FastAPIFileServer(
    root_dir="/data",
    enable_rate_limiting=True,
    rate_limit_requests=50,    # 50 requests
    rate_limit_window=60       # per 60 seconds
)
```

#### Disable Rate Limiting

```python
server = FastAPIFileServer(
    root_dir="/data",
    enable_rate_limiting=False
)
```

**Rate Limit Errors:**
- `429 Too Many Requests`: Rate limit exceeded
- Response includes details about the limit

### 3. Path Traversal Prevention

All file paths are validated to prevent directory traversal attacks.

#### How It Works

1. **Input Validation**: Pydantic validators check for suspicious patterns
2. **Path Resolution**: All paths are resolved relative to the root directory
3. **Boundary Checking**: Resolved paths must stay within the root directory

#### Examples

```python
# Safe paths
"/data/file.txt"        # Within root
"subdir/file.txt"       # Relative path
"./file.txt"            # Current directory

# Blocked paths (raise ValueError)
"../../../etc/passwd"   # Directory traversal
"/../file.txt"          # Traversal attempt
```

**Security Errors:**
- `422 Unprocessable Entity`: Path validation failed (Pydantic)
- `200 OK` with error in content: Path outside root directory

### 4. Input Validation

All request data is validated using Pydantic models before processing.

#### Write Request Validation

```python
class WriteRequest(BaseModel):
    file_path: str          # Required, validated for path traversal
    content: str            # Required

# Example error
{
  "detail": [
    {
      "type": "value_error",
      "msg": "Path traversal detected"
    }
  ]
}
```

#### Edit Request Validation

```python
class EditRequest(BaseModel):
    file_path: str          # Required, validated for path traversal
    old_string: str         # Required
    new_string: str = ""    # Optional, defaults to empty string
    replace_all: bool = False  # Optional, defaults to false
```

**Validation Errors:**
- `422 Unprocessable Entity`: Invalid request data
- Response includes detailed error messages

## API Endpoints

### Public Endpoints

#### Health Check
```
GET /health
```
No authentication required. Returns server status.

### Protected Endpoints

All require `X-API-Key` header.

#### List Directory
```
GET /api/ls?path=/path/to/dir
```

#### Read File
```
GET /api/read?file_path=/path/to/file&offset=0&limit=2000
```

#### Write File
```
POST /api/write
Content-Type: application/json

{
  "file_path": "/path/to/file",
  "content": "file content"
}
```

#### Edit File
```
POST /api/edit
Content-Type: application/json

{
  "file_path": "/path/to/file",
  "old_string": "search",
  "new_string": "replace",
  "replace_all": false
}
```

#### Search Files (Grep)
```
GET /api/grep?pattern=regex&path=/search/path&glob=*.txt
```

#### Pattern Matching (Glob)
```
GET /api/glob?pattern=*.py&path=/search/path
```

## Best Practices

### 1. API Key Management

- **Generate Strong Keys**: Use `secrets.token_urlsafe(32)` or similar
- **Store Securely**: Use environment variables, never commit to version control
- **Rotate Regularly**: Change API keys periodically
- **Use Different Keys**: Different keys for different clients/environments

```python
import os

api_key = os.environ.get("FILESERVER_API_KEY")
if not api_key:
    raise ValueError("FILESERVER_API_KEY environment variable not set")

server = FastAPIFileServer(root_dir="/data", api_key=api_key)
```

### 2. Rate Limiting

- **Production**: Enable rate limiting in production environments
- **API Clients**: Set limits based on expected usage patterns
- **Monitoring**: Log rate limit violations to detect abuse

```python
# Conservative for public API
server = FastAPIFileServer(
    root_dir="/data",
    rate_limit_requests=30,
    rate_limit_window=60
)

# Generous for internal API
server = FastAPIFileServer(
    root_dir="/data",
    rate_limit_requests=1000,
    rate_limit_window=60
)
```

### 3. Root Directory Configuration

- **Isolate Data**: Use a dedicated directory for file operations
- **Restrict Permissions**: Set appropriate file system permissions
- **Monitor Access**: Log all file operations for auditing

```python
# Good: Isolated directory
server = FastAPIFileServer(root_dir="/var/fileserver/data")

# Bad: System directory
server = FastAPIFileServer(root_dir="/")  # Don't do this!
```

### 4. Deployment

#### Behind Reverse Proxy

```nginx
# Nginx configuration
location /fileserver/ {
    proxy_pass http://localhost:8080/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    
    # Optional: Add additional security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
}
```

#### HTTPS/TLS

Always use HTTPS in production:

```python
# Use reverse proxy (nginx, apache) for TLS termination
# Or use uvicorn with SSL
import uvicorn

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8443,
    ssl_keyfile="/path/to/key.pem",
    ssl_certfile="/path/to/cert.pem"
)
```

#### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY libs/deepagents-fileserver /app
RUN pip install -e .

ENV FILESERVER_ROOT=/data
ENV FILESERVER_API_KEY=changeme

VOLUME /data

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "fileserver.server_fastapi:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 5. Monitoring and Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# FastAPI automatically logs requests
# Monitor for:
# - 401 errors (authentication failures)
# - 429 errors (rate limit violations)
# - 422 errors (validation failures)
```

## Testing Security Features

### Test Authentication

```bash
# Should return 401
curl http://localhost:8080/api/ls

# Should return 401
curl -H "X-API-Key: wrong-key" http://localhost:8080/api/ls

# Should return 200
curl -H "X-API-Key: correct-key" http://localhost:8080/api/ls
```

### Test Rate Limiting

```bash
# Make rapid requests
for i in {1..110}; do
  curl -H "X-API-Key: your-key" http://localhost:8080/api/ls
  echo "Request $i"
done

# Should see 429 errors after limit reached
```

### Test Path Traversal Prevention

```bash
# Should return validation error (422)
curl -X POST http://localhost:8080/api/write \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "../../../etc/passwd", "content": "hack"}'

# Should return error in content (200 but error message)
curl -H "X-API-Key: your-key" \
  "http://localhost:8080/api/read?file_path=../../../etc/passwd"
```

## Security Checklist

- [ ] Use strong, randomly generated API keys
- [ ] Store API keys in environment variables, not in code
- [ ] Enable rate limiting in production
- [ ] Use appropriate rate limit values for your use case
- [ ] Set root_dir to an isolated directory with appropriate permissions
- [ ] Deploy behind a reverse proxy with HTTPS/TLS
- [ ] Add additional security headers (CSP, HSTS, etc.) via reverse proxy
- [ ] Monitor logs for authentication failures and rate limit violations
- [ ] Regularly rotate API keys
- [ ] Test security features before deploying to production
- [ ] Keep dependencies updated (uvicorn, fastapi, pydantic)
- [ ] Use network-level restrictions (firewall, VPN) for additional security

## Troubleshooting

### 401 Unauthorized

**Problem**: API requests return 401 Unauthorized

**Solutions**:
- Check that X-API-Key header is included
- Verify API key matches server configuration
- Check for typos in header name or key value

### 429 Too Many Requests

**Problem**: Requests are being rate limited

**Solutions**:
- Wait for rate limit window to reset
- Increase rate limit configuration
- Reduce request frequency from client
- Use different API keys for different clients

### 422 Unprocessable Entity

**Problem**: Request validation fails

**Solutions**:
- Check request body matches expected schema
- Verify file paths don't contain ".."
- Ensure all required fields are present
- Check data types match expected types

## Additional Resources

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Interactive API Documentation](http://localhost:8080/docs) (when server is running)
