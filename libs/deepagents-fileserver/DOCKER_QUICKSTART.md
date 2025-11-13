# Docker Quick Start

Get the FileServer running in Docker in under 2 minutes!

## Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose v2+

## Quick Start

```bash
# 1. Navigate to the fileserver directory
cd libs/deepagents-fileserver

# 2. Start the server (FastAPI with security)
docker compose up -d

# 3. Get your API key from logs
docker compose logs | grep "API Key"

# 4. Test it works
curl http://localhost:8080/health
```

## Basic Usage

### Write a file
```bash
curl -X POST http://localhost:8080/api/write \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"file_path": "/test.txt", "content": "Hello Docker!"}'
```

### Read a file
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://localhost:8080/api/read?file_path=/test.txt"
```

### View API documentation
Open in browser: http://localhost:8080/docs

## Configuration

Edit `docker-compose.yml` or use environment variables:

```yaml
environment:
  - SERVER_TYPE=fastapi  # or 'standard'
  - PORT=8080
  - ROOT_DIR=/data
  - API_KEY=my-secret-key  # optional, auto-generated if not set
```

## Data Persistence

Your files are stored in `./data` directory, automatically created and mounted to `/data` in the container.

```bash
# Check your files
ls -la ./data/
```

## Stop and Cleanup

```bash
# Stop the server
docker compose down

# Stop and remove volumes
docker compose down -v
```

## Troubleshooting

### Port already in use
Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8888:8080"  # Use 8888 on host instead
```

### Permission denied
```bash
# Fix data directory permissions
chmod -R 755 ./data
```

### Build fails with network errors
If you see DNS resolution errors during build, try:
```bash
# Use host network for building
docker build --network=host -t deepagents-fileserver .

# Or configure Docker DNS
# Edit /etc/docker/daemon.json:
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
# Then restart Docker: sudo systemctl restart docker
```

### Can't connect to API
```bash
# Check if container is running
docker ps

# Check logs
docker compose logs -f

# Check health status
docker inspect deepagents-fileserver-fastapi | grep Health -A 10
```

## Next Steps

- Read [DOCKER.md](DOCKER.md) for complete documentation
- See [README.md](README.md) for API reference
- Check [FASTAPI_SECURITY_GUIDE.md](FASTAPI_SECURITY_GUIDE.md) for security best practices
- Run automated tests: `./test_docker.sh`

## Common Patterns

### Custom API key
```bash
docker compose up -d -e API_KEY=my-secure-key
```

### Different port
```bash
docker run -p 9000:8080 -v $(pwd)/data:/data deepagents-fileserver
```

### Read-only data
```bash
docker run -v /my/readonly/data:/data:ro deepagents-fileserver
```

### Standard server (no auth)
```bash
docker compose --profile standard up fileserver-standard -d
```

## Production Deployment

For production, see [DOCKER.md](DOCKER.md) for:
- HTTPS/TLS configuration
- Reverse proxy setup (nginx)
- Kubernetes deployment
- Security hardening
- Monitoring and logging
- Resource limits

## Getting Help

- View container logs: `docker compose logs -f`
- Get container status: `docker ps`
- Inspect container: `docker inspect deepagents-fileserver-fastapi`
- Interactive shell: `docker exec -it deepagents-fileserver-fastapi sh`
