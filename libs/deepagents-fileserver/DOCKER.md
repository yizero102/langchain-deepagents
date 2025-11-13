# Docker Guide for DeepAgents FileServer

This guide covers running the FileServer in Docker containers for production deployment.

## Quick Start

### Using Docker Compose (Recommended)

The easiest way to run the FileServer is using Docker Compose:

```bash
# Start FastAPI server (recommended)
docker-compose up -d

# View logs and get the auto-generated API key
docker-compose logs -f fileserver-fastapi

# Stop the server
docker-compose down
```

The server will be available at `http://localhost:8080` with your data mounted at `./data`.

### Using Docker CLI

Build and run manually:

```bash
# Build the image
docker build -t deepagents-fileserver .

# Run FastAPI server
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e SERVER_TYPE=fastapi \
  deepagents-fileserver

# View logs to get the API key
docker logs fileserver

# Run standard server (no authentication)
docker run -d \
  --name fileserver-standard \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e SERVER_TYPE=standard \
  deepagents-fileserver
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_TYPE` | `fastapi` | Server type: `fastapi` or `standard` |
| `PORT` | `8080` | Port to listen on |
| `ROOT_DIR` | `/data` | Root directory for file operations |
| `API_KEY` | *auto-generated* | API key for FastAPI server (if not set, auto-generated) |

### Volume Mounts

Mount your data directory to `/data` in the container:

```bash
docker run -v /path/to/your/data:/data deepagents-fileserver
```

## Docker Compose Configurations

### FastAPI Server (Production)

Default configuration in `docker-compose.yml`:

```yaml
services:
  fileserver-fastapi:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    environment:
      - SERVER_TYPE=fastapi
      - PORT=8080
      - ROOT_DIR=/data
    restart: unless-stopped
```

**Usage:**
```bash
docker-compose up -d
docker-compose logs -f  # Get API key from logs
```

### Standard Server (Development)

Enable with profile:

```bash
docker-compose --profile standard up fileserver-standard -d
```

This starts the standard server on port 8081.

### Custom Configuration

Create a `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  fileserver-fastapi:
    environment:
      - API_KEY=my-secret-key
      - PORT=9000
    ports:
      - "9000:9000"
    volumes:
      - /custom/path:/data
```

Then run:
```bash
docker-compose up -d
```

## Security Considerations

### API Key Management

**Option 1: Auto-generated (Recommended for development)**
```bash
docker-compose up -d
docker-compose logs | grep "API Key"
```

**Option 2: Custom key (Recommended for production)**
```bash
# Set via environment variable
docker run -e API_KEY=your-secure-key-here deepagents-fileserver

# Or in docker-compose.yml
environment:
  - API_KEY=your-secure-key-here
```

**Option 3: Using secrets (Production best practice)**
```yaml
services:
  fileserver-fastapi:
    secrets:
      - api_key
    environment:
      - API_KEY_FILE=/run/secrets/api_key

secrets:
  api_key:
    file: ./secrets/api_key.txt
```

### Network Security

**Run on localhost only:**
```bash
docker run -p 127.0.0.1:8080:8080 deepagents-fileserver
```

**Use Docker networks:**
```yaml
services:
  fileserver-fastapi:
    networks:
      - internal

networks:
  internal:
    internal: true  # No external access
```

**Behind reverse proxy (recommended for production):**
```yaml
services:
  fileserver-fastapi:
    expose:
      - 8080
    networks:
      - internal
  
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    networks:
      - internal
```

### File Permissions

The container runs as a non-root user (`fileserver`, UID 1000) for security:

```bash
# Ensure your data directory has correct permissions
chmod -R 755 ./data
```

If you need a different UID:
```bash
docker run --user 1001:1001 deepagents-fileserver
```

## Production Deployment

### Complete Production Setup

```yaml
version: '3.8'

services:
  fileserver:
    build: .
    container_name: deepagents-fileserver
    restart: always
    expose:
      - 8080
    volumes:
      - /production/data:/data:ro  # Read-only mount
    environment:
      - SERVER_TYPE=fastapi
      - API_KEY_FILE=/run/secrets/api_key
    secrets:
      - api_key
    networks:
      - internal
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"]
      interval: 30s
      timeout: 5s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    networks:
      - internal
    depends_on:
      - fileserver

secrets:
  api_key:
    file: ./secrets/api_key.txt

networks:
  internal:
    name: fileserver-network
```

### Resource Limits

Limit container resources:

```yaml
services:
  fileserver-fastapi:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Monitoring

**Health checks:**
```bash
docker inspect --format='{{.State.Health.Status}}' fileserver
```

**Logs:**
```bash
docker logs -f --tail=100 fileserver
```

**Stats:**
```bash
docker stats fileserver
```

## Testing the Docker Setup

### Basic Test

```bash
# Start server
docker-compose up -d

# Get API key from logs
API_KEY=$(docker-compose logs fileserver-fastapi | grep "API Key:" | awk '{print $NF}')

# Test health endpoint
curl http://localhost:8080/health

# Test authenticated endpoint (FastAPI)
curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/ls

# Write a test file
curl -X POST http://localhost:8080/api/write \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"file_path": "test.txt", "content": "Hello Docker!"}'

# Read it back
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8080/api/read?file_path=test.txt"

# Verify file in mounted volume
cat ./data/test.txt
```

### Automated Test Script

Save as `test_docker.sh`:

```bash
#!/bin/bash
set -e

echo "Starting FileServer..."
docker-compose up -d

echo "Waiting for server to be ready..."
sleep 3

echo "Getting API key..."
API_KEY=$(docker-compose logs fileserver-fastapi | grep "API Key:" | awk '{print $NF}')

echo "Testing health endpoint..."
curl -f http://localhost:8080/health

echo "Testing write operation..."
curl -f -X POST http://localhost:8080/api/write \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"file_path": "docker-test.txt", "content": "Docker test successful!"}'

echo "Testing read operation..."
curl -f -H "X-API-Key: $API_KEY" \
  "http://localhost:8080/api/read?file_path=docker-test.txt"

echo "All tests passed!"
docker-compose down
```

Run it:
```bash
chmod +x test_docker.sh
./test_docker.sh
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Check container status
docker ps -a

# Inspect container
docker inspect fileserver
```

### Permission denied errors

```bash
# Fix data directory permissions
sudo chown -R 1000:1000 ./data

# Or run with your user ID
docker-compose run --user $(id -u):$(id -g) fileserver-fastapi
```

### Port already in use

```bash
# Change port in docker-compose.yml
ports:
  - "8888:8080"  # Use 8888 on host

# Or use Docker CLI
docker run -p 8888:8080 deepagents-fileserver
```

### Health check failing

```bash
# Check if server is responding
docker exec fileserver curl http://localhost:8080/health

# Check server logs
docker logs fileserver

# Disable health check temporarily
docker run --no-healthcheck deepagents-fileserver
```

## Advanced Usage

### Multi-server Setup

Run multiple FileServer instances:

```yaml
services:
  fileserver-prod:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - /prod/data:/data
    environment:
      - API_KEY=prod-key

  fileserver-dev:
    build: .
    ports:
      - "8081:8080"
    volumes:
      - /dev/data:/data
    environment:
      - API_KEY=dev-key
```

### Custom Entrypoint

Override the entrypoint for debugging:

```bash
docker run -it --entrypoint /bin/bash deepagents-fileserver
```

### Build Arguments

Customize build:

```dockerfile
# In Dockerfile
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim
```

```bash
docker build --build-arg PYTHON_VERSION=3.12 -t deepagents-fileserver .
```

## Performance Optimization

### Layer Caching

The Dockerfile uses multi-stage builds and proper layer ordering for optimal caching.

### Image Size

Current image size: ~150MB (Python 3.11-slim + dependencies)

Reduce further:
```dockerfile
FROM python:3.11-alpine  # Smaller base (~50MB saved)
```

Note: Alpine may have compatibility issues with some Python packages.

### Memory Usage

Typical memory usage:
- Standard server: ~30-50MB
- FastAPI server: ~50-80MB

Increase for large files or many concurrent requests.

## Integration Examples

### With Java SandboxBackend

```java
// Java code using SandboxBackend
SandboxBackend backend = new SandboxBackend(
    "http://localhost:8080",
    "your-api-key"
);
backend.write("/test.txt", "Hello from Java!");
```

### With Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fileserver
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: fileserver
        image: deepagents-fileserver:latest
        ports:
        - containerPort: 8080
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: fileserver-secret
              key: api-key
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: fileserver-pvc
```

## License

MIT License - See LICENSE file for details
