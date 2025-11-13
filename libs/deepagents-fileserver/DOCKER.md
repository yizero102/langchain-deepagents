# Docker Deployment Guide

This guide explains how to run the DeepAgents FileServer in Docker containers.

## Quick Start

### Using Docker Compose (Recommended)

The easiest way to run the FileServer is with Docker Compose:

```bash
# Build and start the FastAPI server (recommended)
docker-compose up -d fileserver-fastapi

# View logs to get the auto-generated API key
docker-compose logs fileserver-fastapi

# Check health
curl http://localhost:8080/health
```

The server will be available at `http://localhost:8080` with data persisted in a Docker volume.

### Using Docker CLI

```bash
# Build the image
docker build -t deepagents-fileserver .

# Run the FastAPI server
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v fileserver-data:/data \
  -e FILESERVER_MODE=fastapi \
  deepagents-fileserver

# View logs to get the API key
docker logs fileserver
```

## Configuration

### Environment Variables

Configure the FileServer using these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FILESERVER_ROOT_DIR` | `/data` | Root directory for file operations |
| `FILESERVER_HOST` | `0.0.0.0` | Host to bind to |
| `FILESERVER_PORT` | `8080` | Port to listen on |
| `FILESERVER_MODE` | `fastapi` | Server mode: `fastapi` or `standard` |
| `FILESERVER_API_KEY` | (auto-generated) | API key for FastAPI mode |

### Docker Compose Configuration

#### FastAPI Server (Production)

```yaml
services:
  fileserver:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data  # Mount local directory
    environment:
      - FILESERVER_MODE=fastapi
      - FILESERVER_API_KEY=my-secure-key-123
```

#### Standard Server (Development)

```yaml
services:
  fileserver:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    environment:
      - FILESERVER_MODE=standard
```

## Usage Examples

### 1. FastAPI Server with Custom API Key

```bash
# Using docker-compose.yml (edit the file first to set API key)
docker-compose up -d

# Or using Docker CLI
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e FILESERVER_MODE=fastapi \
  -e FILESERVER_API_KEY=my-secret-key \
  deepagents-fileserver
```

Test with curl:

```bash
# Health check (no auth required)
curl http://localhost:8080/health

# List files (requires API key)
curl -H "X-API-Key: my-secret-key" \
  "http://localhost:8080/api/ls?path=/"

# Write a file
curl -X POST \
  -H "X-API-Key: my-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/test.txt", "content": "Hello Docker!"}' \
  http://localhost:8080/api/write

# Read the file
curl -H "X-API-Key: my-secret-key" \
  "http://localhost:8080/api/read?file_path=/test.txt"
```

### 2. Standard Server (No Authentication)

```bash
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  -e FILESERVER_MODE=standard \
  deepagents-fileserver
```

Test with curl:

```bash
# No API key needed
curl "http://localhost:8080/api/ls?path=/"
curl "http://localhost:8080/api/read?file_path=/test.txt"
```

### 3. Custom Port and Directory

```bash
docker run -d \
  --name fileserver \
  -p 9000:9000 \
  -v /path/to/data:/mydata \
  -e FILESERVER_PORT=9000 \
  -e FILESERVER_ROOT_DIR=/mydata \
  -e FILESERVER_MODE=fastapi \
  deepagents-fileserver
```

### 4. Multiple Instances

Run both FastAPI and Standard servers simultaneously:

```bash
# Start both services
docker-compose up -d

# FastAPI server on port 8080
curl http://localhost:8080/health

# Standard server on port 8081
docker-compose --profile standard up -d fileserver-standard
curl http://localhost:8081/health
```

## Data Persistence

### Using Docker Volumes (Recommended)

Docker volumes provide persistent storage managed by Docker:

```bash
# Create a named volume
docker volume create fileserver-data

# Run with the volume
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v fileserver-data:/data \
  deepagents-fileserver

# List volumes
docker volume ls

# Inspect volume
docker volume inspect fileserver-data

# Backup volume
docker run --rm -v fileserver-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/fileserver-backup.tar.gz /data
```

### Using Bind Mounts

Bind mounts link a host directory to the container:

```bash
# Create directory on host
mkdir -p ~/fileserver-data

# Run with bind mount
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v ~/fileserver-data:/data \
  deepagents-fileserver

# Files in ~/fileserver-data are now accessible via the API
```

## Health Checks

The container includes a built-in health check:

```bash
# Check container health
docker ps

# View health check logs
docker inspect fileserver --format='{{.State.Health.Status}}'

# Manual health check
curl http://localhost:8080/health
```

## Logs and Monitoring

```bash
# View real-time logs
docker logs -f fileserver

# View last 100 lines
docker logs --tail 100 fileserver

# With docker-compose
docker-compose logs -f fileserver-fastapi
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs fileserver

# Check environment variables
docker inspect fileserver | jq '.[0].Config.Env'

# Verify volume mounts
docker inspect fileserver | jq '.[0].Mounts'
```

### Permission Issues

If you encounter permission issues with bind mounts:

```bash
# Run as specific user (replace 1000:1000 with your UID:GID)
docker run -d \
  --name fileserver \
  --user 1000:1000 \
  -p 8080:8080 \
  -v $(pwd)/data:/data \
  deepagents-fileserver
```

### Port Already in Use

```bash
# Use a different port
docker run -d \
  --name fileserver \
  -p 9000:8080 \
  -v fileserver-data:/data \
  deepagents-fileserver

# Access on new port
curl http://localhost:9000/health
```

### Cannot Connect to Server

```bash
# Check if container is running
docker ps -a

# Check port mapping
docker port fileserver

# Check if server is listening
docker exec fileserver netstat -tlnp | grep 8080

# Check firewall rules (on host)
sudo ufw status
```

## Production Deployment

### Best Practices

1. **Use FastAPI Mode**: Always use FastAPI mode in production for security
2. **Set Custom API Key**: Never use auto-generated keys in production
3. **Use Volumes**: Use Docker volumes for data persistence
4. **Enable Restart Policy**: Configure automatic restart on failure
5. **Reverse Proxy**: Run behind nginx or Traefik for SSL termination
6. **Resource Limits**: Set memory and CPU limits

### Production Docker Compose

```yaml
version: '3.8'

services:
  fileserver:
    build: .
    container_name: fileserver-prod
    ports:
      - "127.0.0.1:8080:8080"  # Only localhost access
    volumes:
      - fileserver-data:/data
    environment:
      - FILESERVER_MODE=fastapi
      - FILESERVER_API_KEY=${API_KEY}  # From .env file
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  fileserver-data:
    driver: local
```

Create `.env` file:

```bash
API_KEY=your-super-secret-production-api-key-here
```

### Behind Nginx Reverse Proxy

nginx configuration:

```nginx
server {
    listen 80;
    server_name fileserver.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Docker Hub Deployment

### Build and Tag

```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t username/deepagents-fileserver:latest \
  -t username/deepagents-fileserver:0.2.0 \
  --push .
```

### Pull and Run

```bash
# Pull from registry
docker pull username/deepagents-fileserver:latest

# Run
docker run -d \
  --name fileserver \
  -p 8080:8080 \
  -v fileserver-data:/data \
  username/deepagents-fileserver:latest
```

## Cleaning Up

```bash
# Stop container
docker stop fileserver
# or
docker-compose down

# Remove container
docker rm fileserver

# Remove image
docker rmi deepagents-fileserver

# Remove volume (WARNING: deletes all data)
docker volume rm fileserver-data

# Clean up everything
docker-compose down -v
docker system prune -a
```

## API Documentation

When running the FastAPI server, interactive API documentation is available at:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## Security Notes

1. **API Keys**: Always set `FILESERVER_API_KEY` in production
2. **Network**: Bind to `127.0.0.1` if only local access is needed
3. **Volumes**: Be careful with bind mounts and file permissions
4. **Updates**: Regularly update the base image and dependencies
5. **Secrets**: Use Docker secrets or environment files, never hardcode

## Support

For issues or questions:
- Check logs: `docker logs fileserver`
- Review README.md for API details
- See FASTAPI_SECURITY_GUIDE.md for security best practices
