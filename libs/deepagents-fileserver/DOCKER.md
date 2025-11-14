# Docker Deployment Guide for DeepAgents FileServer

This guide covers how to build, run, and test the DeepAgents FileServer using Docker.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start FastAPI server (recommended for production)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop server
docker-compose down
```

The server will be available at `http://localhost:8080`. The API key will be auto-generated and displayed in the logs.

### Using Docker CLI

```bash
# Build the image
docker build -t deepagents-fileserver .

# Run FastAPI server (with custom API key)
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e FILESERVER_API_KEY=your-secret-key \
  deepagents-fileserver

# Run Standard server (no authentication)
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  deepagents-fileserver fileserver.server /data 8080
```

## Configuration

### Environment Variables

#### FastAPI Server

- `FILESERVER_API_KEY`: Custom API key (optional, auto-generated if not set)
- `FILESERVER_RATE_LIMIT_REQUESTS`: Maximum requests per window (default: 100)
- `FILESERVER_RATE_LIMIT_WINDOW`: Rate limit window in seconds (default: 60)

### Volume Mounting

The container expects a data directory at `/data`. Mount your local directory to this path:

```bash
# Linux/macOS
-v /path/to/your/data:/data

# Windows (PowerShell)
-v C:\path\to\your\data:/data

# Windows (CMD)
-v C:\path\to\your\data:/data
```

### Port Mapping

The default port inside the container is `8080`. Map it to any port on your host:

```bash
# Map to host port 9000
-p 9000:8080

# Map to all interfaces
-p 0.0.0.0:8080:8080
```

## docker-compose.yml Options

### FastAPI Server (Default)

```yaml
services:
  fileserver-fastapi:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    environment:
      - FILESERVER_API_KEY=your-secret-key
      - FILESERVER_RATE_LIMIT_REQUESTS=100
      - FILESERVER_RATE_LIMIT_WINDOW=60
    restart: unless-stopped
```

### Standard Server

```yaml
services:
  fileserver-standard:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    command: ["fileserver.server", "/data", "8080"]
    restart: unless-stopped
```

### Running Both Servers

The included `docker-compose.yml` supports running both servers simultaneously on different ports:

```bash
# Start FastAPI server on port 8080
docker-compose up -d fileserver-fastapi

# Start Standard server on port 8081
docker-compose --profile standard up -d fileserver-standard

# Start both
docker-compose --profile standard up -d
```

## Testing

### Automated Test Suite

Run the comprehensive test script:

```bash
cd libs/deepagents-fileserver
./test_docker.sh
```

This script will:
1. Build the Docker image
2. Test the FastAPI server (with authentication)
3. Test the Standard server
4. Verify all API endpoints (health, write, read, list, edit, grep, glob)
5. Clean up containers and test data

### Manual Testing

#### Health Check

```bash
curl http://localhost:8080/health
```

#### FastAPI Server (with API key)

```bash
# Set your API key
API_KEY="your-secret-key"

# List directory
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8080/api/ls?path=/"

# Write file
curl -X POST -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test.txt", "content": "Hello World"}' \
  http://localhost:8080/api/write

# Read file
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8080/api/read?file_path=test.txt"
```

#### Standard Server (no authentication)

```bash
# List directory
curl "http://localhost:8080/api/ls?path=/"

# Write file
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test.txt", "content": "Hello World"}' \
  http://localhost:8080/api/write
```

## Production Deployment

### Security Best Practices

1. **Always use FastAPI server** for production deployments
2. **Set a strong API key**:
   ```bash
   # Generate a secure random key
   openssl rand -base64 32
   ```
3. **Use HTTPS** with a reverse proxy (nginx, Traefik, etc.)
4. **Limit volume access** to only necessary directories
5. **Run as non-root user** (add to Dockerfile if needed)
6. **Configure rate limiting** appropriately for your use case
7. **Use Docker secrets** for API key management in swarm mode

### Example with Nginx Reverse Proxy

```yaml
version: '3.8'

services:
  fileserver:
    build: .
    expose:
      - "8080"
    volumes:
      - ./data:/data
    environment:
      - FILESERVER_API_KEY=${API_KEY}
    networks:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - fileserver
    networks:
      - backend

networks:
  backend:
    driver: bridge
```

### Docker Swarm / Kubernetes

For orchestration platforms, see the deployment examples:

- **Docker Swarm**: Use `docker stack deploy` with secrets
- **Kubernetes**: See `k8s-deployment.yaml` (create if needed)

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs fileserver

# Check if port is already in use
netstat -tuln | grep 8080
```

### Permission errors

```bash
# Ensure the data directory is writable
chmod 755 ./data

# Or run with user permissions
docker run --user $(id -u):$(id -g) ...
```

### Health check failing

```bash
# Test manually
docker exec fileserver curl http://localhost:8080/health

# Check if server is running
docker exec fileserver ps aux
```

### Volume not mounting

```bash
# Use absolute paths
docker run -v /absolute/path/to/data:/data ...

# Check Docker volume permissions
docker inspect fileserver | grep -A 10 Mounts
```

## Advanced Usage

### Custom Base Directory

Run the server with a different base directory inside the container:

```bash
docker run -d \
  -v /host/path1:/custom/dir1 \
  -v /host/path2:/custom/dir2 \
  deepagents-fileserver fileserver.server_fastapi /custom/dir1 8080
```

### Multi-stage Build for Smaller Images

The Dockerfile uses multi-stage builds to minimize image size. To further optimize:

```dockerfile
FROM python:3.11-alpine as base
# ... alpine-based build
```

### Running Tests Inside Container

```bash
# Install test dependencies
docker run --rm deepagents-fileserver pip install pytest httpx

# Run tests
docker run --rm -v $(pwd)/tests:/app/tests deepagents-fileserver pytest
```

## Image Information

- **Base Image**: `python:3.11-slim`
- **Size**: ~150-200 MB (approximate)
- **Exposed Ports**: 8080
- **Volumes**: `/data` (default working directory)
- **Health Check**: Enabled (checks `/health` endpoint every 30s)
- **Default Command**: FastAPI server on `/data`

## Building for Different Platforms

### Multi-architecture Build

```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -t deepagents-fileserver:latest \
  --push .
```

### Optimized Build

```bash
# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build -t deepagents-fileserver .

# Build with cache from registry
docker build \
  --cache-from deepagents-fileserver:latest \
  -t deepagents-fileserver:latest .
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Test Docker Image

on: [push, pull_request]

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t deepagents-fileserver .
      
      - name: Run tests
        run: cd libs/deepagents-fileserver && ./test_docker.sh
```

### GitLab CI Example

```yaml
docker-build:
  stage: build
  script:
    - docker build -t deepagents-fileserver .
    - cd libs/deepagents-fileserver
    - ./test_docker.sh
  only:
    - main
    - develop
```

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Review [FASTAPI_SECURITY_GUIDE.md](FASTAPI_SECURITY_GUIDE.md)
- Open an issue on GitHub

## License

MIT License - See LICENSE file for details
