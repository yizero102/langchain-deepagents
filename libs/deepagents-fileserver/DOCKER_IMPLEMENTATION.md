# Docker Implementation for DeepAgents FileServer

## Overview

The DeepAgents FileServer has been successfully dockerized with a complete implementation including:

1. **Dockerfile** - Production-ready multi-stage build
2. **docker-compose.yml** - Easy orchestration for both server modes
3. **docker-entrypoint.sh** - Flexible entry point script with environment configuration
4. **.dockerignore** - Optimized build context
5. **DOCKER.md** - Comprehensive deployment and usage guide
6. **Test scripts** - Automated verification tools

## Files Added

### Core Docker Files

1. **Dockerfile**
   - Based on `python:3.11-slim`
   - Installs FastAPI, Uvicorn, and Pydantic
   - Creates `/data` directory for file operations
   - Configurable via environment variables
   - Health check using Python's urllib
   - Exposes port 8080

2. **docker-entrypoint.sh**
   - Bash script that handles server startup
   - Supports both `fastapi` and `standard` modes
   - Configurable via environment variables:
     - `FILESERVER_ROOT_DIR` (default: `/data`)
     - `FILESERVER_HOST` (default: `0.0.0.0`)
     - `FILESERVER_PORT` (default: `8080`)
     - `FILESERVER_MODE` (default: `fastapi`)
     - `FILESERVER_API_KEY` (optional, auto-generated if not provided)

3. **docker-compose.yml**
   - Two service configurations:
     - `fileserver-fastapi`: Production-ready with auth (port 8080)
     - `fileserver-standard`: Simple mode (port 8081, requires `--profile standard`)
   - Named volume `fileserver-data` for data persistence
   - Health checks configured
   - Restart policy: `unless-stopped`

4. **.dockerignore**
   - Excludes build artifacts, tests, and documentation
   - Optimizes build context size

### Documentation

5. **DOCKER.md** - Comprehensive guide covering:
   - Quick start instructions
   - Configuration options
   - Usage examples (curl and Python)
   - Data persistence strategies (volumes vs bind mounts)
   - Health checks and monitoring
   - Production deployment best practices
   - Troubleshooting guide
   - Security considerations

6. **Updated README.md**
   - Added "Docker Support" section to features
   - Added "Option 3: Docker" to Quick Start
   - References to DOCKER.md

### Testing Scripts

7. **test_docker.py**
   - Comprehensive Python test script
   - Tests both FastAPI and Standard server modes
   - Automated container lifecycle management
   - Tests all API endpoints:
     - Health check
     - List directory
     - Write file
     - Read file
     - Edit file
     - Grep search
     - Glob pattern
     - API documentation (FastAPI only)

8. **manual_docker_test.sh**
   - Bash script for manual testing
   - Step-by-step verification
   - Interactive mode with detailed output
   - Colored output for easy readability

## Features Implemented

### 1. Multi-Mode Support
- **FastAPI Mode** (default): Production-ready with API key authentication
- **Standard Mode**: Simple HTTP server without dependencies

### 2. Configuration
All aspects configurable via environment variables:
```bash
FILESERVER_ROOT_DIR=/data
FILESERVER_HOST=0.0.0.0
FILESERVER_PORT=8080
FILESERVER_MODE=fastapi
FILESERVER_API_KEY=your-key-here
```

### 3. Data Persistence
- Docker volumes (recommended)
- Bind mounts for direct access
- Configurable root directory

### 4. Health Monitoring
- Built-in health check endpoint (`/health`)
- Docker health check configured
- 30-second intervals with retry logic

### 5. Security
- API key authentication in FastAPI mode
- Path traversal prevention
- Input validation
- Rate limiting support
- Can run behind reverse proxy

## Usage Examples

### Quick Start with Docker Compose

```bash
# Navigate to fileserver directory
cd libs/deepagents-fileserver

# Start FastAPI server
docker-compose up -d fileserver-fastapi

# View logs (contains auto-generated API key)
docker-compose logs fileserver-fastapi

# Test health
curl http://localhost:8080/health
```

### Docker CLI Usage

```bash
# Build image
docker build -t deepagents-fileserver .

# Run FastAPI server
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v fileserver-data:/data \
  -e FILESERVER_MODE=fastapi \
  -e FILESERVER_API_KEY=my-secret-key \
  deepagents-fileserver

# View logs
docker logs -f fileserver

# Test API
curl -H "X-API-Key: my-secret-key" \
  "http://localhost:8080/api/ls?path=/"
```

### API Testing

```bash
# Health check (no auth required)
curl http://localhost:8080/health

# Write a file
curl -X POST \
  -H "X-API-Key: my-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/test.txt", "content": "Hello Docker!"}' \
  http://localhost:8080/api/write

# Read the file
curl -H "X-API-Key: my-secret-key" \
  "http://localhost:8080/api/read?file_path=/test.txt"

# List files
curl -H "X-API-Key: my-secret-key" \
  "http://localhost:8080/api/ls?path=/"
```

## Verification Steps

### Manual Verification

1. **Build the image**:
   ```bash
   cd libs/deepagents-fileserver
   docker build -t deepagents-fileserver .
   ```

2. **Start a container**:
   ```bash
   docker run -d --name test-fs -p 8080:8080 \
     -e FILESERVER_MODE=fastapi \
     -e FILESERVER_API_KEY=test-key \
     deepagents-fileserver
   ```

3. **Check health**:
   ```bash
   curl http://localhost:8080/health
   # Expected: {"status":"ok"}
   ```

4. **Test write operation**:
   ```bash
   curl -X POST \
     -H "X-API-Key: test-key" \
     -H "Content-Type: application/json" \
     -d '{"file_path": "/hello.txt", "content": "Hello World"}' \
     http://localhost:8080/api/write
   # Expected: {"error":null,"path":"/hello.txt"}
   ```

5. **Test read operation**:
   ```bash
   curl -H "X-API-Key: test-key" \
     "http://localhost:8080/api/read?file_path=/hello.txt"
   # Expected: Content with "Hello World"
   ```

6. **Access API docs**:
   ```bash
   # Open in browser
   open http://localhost:8080/docs
   ```

7. **Cleanup**:
   ```bash
   docker stop test-fs
   docker rm test-fs
   ```

### Automated Testing

Run the Python test script:
```bash
python3 test_docker.py
```

Or use the bash script:
```bash
./manual_docker_test.sh
```

## Integration with Existing Systems

### With Java SandboxBackend

The dockerized FileServer works seamlessly with the Java SandboxBackend:

```java
import com.deepagents.backends.SandboxBackend;

SandboxBackend backend = new SandboxBackend(
    "http://localhost:8080/api",
    "my-secret-key"
);

// Use all backend operations
backend.write("/test.txt", "Hello from Java!");
String content = backend.read("/test.txt", 0, 100);
```

### With Python Clients

```python
import requests

BASE_URL = "http://localhost:8080"
API_KEY = "my-secret-key"
headers = {"X-API-Key": API_KEY}

# Write
requests.post(
    f"{BASE_URL}/api/write",
    json={"file_path": "/test.txt", "content": "Hello!"},
    headers=headers
)

# Read
response = requests.get(
    f"{BASE_URL}/api/read",
    params={"file_path": "/test.txt"},
    headers=headers
)
print(response.json())
```

## Production Considerations

### Security
1. Always use FastAPI mode in production
2. Set a strong API key via `FILESERVER_API_KEY`
3. Run behind a reverse proxy (nginx, Traefik)
4. Enable TLS/SSL
5. Bind to `127.0.0.1` if only local access needed

### Performance
1. Use Docker volumes for better I/O performance
2. Set resource limits in docker-compose.yml
3. Enable rate limiting in FastAPI mode
4. Monitor container health

### Deployment
1. Use docker-compose for easy orchestration
2. Configure restart policies
3. Set up log rotation
4. Use named volumes for data persistence
5. Backup volumes regularly

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs <container-name>

# Check if port is available
netstat -tlnp | grep 8080

# Try different port
docker run -p 9000:8080 ...
```

### Cannot Connect
```bash
# Verify container is running
docker ps

# Check health status
docker inspect <container-name> | grep Health

# Test from inside container
docker exec <container-name> curl http://localhost:8080/health
```

### Permission Issues
```bash
# Run as specific user
docker run --user 1000:1000 ...

# Or fix permissions on bind mount
chmod -R 755 /path/to/data
```

## Summary

The FileServer is now fully dockerized and production-ready with:

✅ Complete Docker setup (Dockerfile, docker-compose.yml, entrypoint script)
✅ Comprehensive documentation (DOCKER.md)
✅ Automated and manual test scripts
✅ Security features (API key auth, health checks)
✅ Flexible configuration via environment variables
✅ Data persistence options (volumes and bind mounts)
✅ Integration examples for Java and Python clients
✅ Production deployment guidelines

The implementation follows Docker best practices and is ready for deployment in development, staging, and production environments.
