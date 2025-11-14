# Docker Quick Start Guide

Get the DeepAgents FileServer running in Docker in under 5 minutes.

## Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (included with Docker Desktop)

## 1. Quick Start with docker-compose (Recommended)

```bash
# Navigate to the fileserver directory
cd libs/deepagents-fileserver

# Start the server
docker-compose up -d

# View the API key in logs (auto-generated)
docker-compose logs fileserver-fastapi | grep "API Key"

# Check server status
curl http://localhost:8080/health
```

The FastAPI server is now running at `http://localhost:8080` with:
- ✅ API key authentication
- ✅ Rate limiting
- ✅ Path traversal prevention
- ✅ OpenAPI docs at `/docs`

## 2. Quick Start with Docker CLI

```bash
# Build the image
docker build -t deepagents-fileserver .

# Run with custom API key
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e FILESERVER_API_KEY=my-secret-key \
  deepagents-fileserver

# Check logs
docker logs fileserver
```

## 3. Test the Server

### Using curl with API Key

```bash
# Set your API key (from logs or custom)
export API_KEY="your-api-key"

# Health check (no auth required)
curl http://localhost:8080/health

# List directory
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8080/api/ls?path=/"

# Write a file
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "hello.txt", "content": "Hello Docker!"}' \
  http://localhost:8080/api/write

# Read the file
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8080/api/read?file_path=hello.txt"
```

### Using the Test Script

```bash
# Run comprehensive tests
./test_docker.sh
```

## 4. Access Interactive API Documentation

Open your browser and visit:
```
http://localhost:8080/docs
```

You'll see the full OpenAPI documentation with a "Try it out" interface.

## 5. Stop and Clean Up

```bash
# Stop the server
docker-compose down

# Or with Docker CLI
docker stop fileserver
docker rm fileserver

# Remove the image (optional)
docker rmi deepagents-fileserver
```

## Common Commands

### View Logs
```bash
docker-compose logs -f fileserver-fastapi
```

### Restart Server
```bash
docker-compose restart fileserver-fastapi
```

### Run Standard Server (no auth)
```bash
docker-compose --profile standard up -d fileserver-standard
```

### Custom Configuration
```bash
# Edit .env file (copy from .env.example)
cp .env.example .env
# Edit .env with your settings
nano .env
# Start with custom config
docker-compose up -d
```

## Troubleshooting

### Port Already in Use
```bash
# Change port in docker-compose.yml
# From: - "8080:8080"
# To:   - "9000:8080"
```

### Permission Issues
```bash
# Ensure data directory is writable
mkdir -p data
chmod 755 data
```

### Can't Connect to Server
```bash
# Check if container is running
docker ps | grep fileserver

# Check container logs
docker logs deepagents-fileserver-fastapi
```

## Next Steps

- Read [DOCKER.md](DOCKER.md) for complete documentation
- Review [FASTAPI_SECURITY_GUIDE.md](FASTAPI_SECURITY_GUIDE.md) for security best practices
- Check [README.md](README.md) for API endpoint details

## Production Deployment

For production:
1. ✅ Use FastAPI server (default)
2. ✅ Set a strong API key: `openssl rand -base64 32`
3. ✅ Use HTTPS with a reverse proxy (nginx, Traefik)
4. ✅ Configure rate limiting appropriately
5. ✅ Limit volume access to necessary directories only
6. ✅ Monitor logs and health checks

See [DOCKER.md](DOCKER.md) for production deployment examples.
