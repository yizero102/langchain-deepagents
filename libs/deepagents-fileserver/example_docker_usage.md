# Docker Usage Examples

This file provides practical examples of using the dockerized FileServer.

## Basic Setup

### 1. Start the Server

```bash
cd libs/deepagents-fileserver
docker compose up -d
```

### 2. Get the API Key

```bash
# View logs and look for "API Key: xxx"
docker compose logs | grep "API Key"

# Or save it to a variable
export API_KEY=$(docker compose logs 2>&1 | grep -oP 'API Key: \K[a-zA-Z0-9-]+' | head -1)
echo "Your API Key: $API_KEY"
```

## Usage Examples

### Python Client

```python
import requests

BASE_URL = "http://localhost:8080"
API_KEY = "your-api-key-here"  # Replace with actual key

headers = {"X-API-Key": API_KEY}

# Write a file
response = requests.post(
    f"{BASE_URL}/api/write",
    json={"file_path": "/hello.txt", "content": "Hello from Python!"},
    headers=headers
)
print(response.json())

# Read the file
response = requests.get(
    f"{BASE_URL}/api/read",
    params={"file_path": "/hello.txt"},
    headers=headers
)
print(response.json()["content"])

# Search for content
response = requests.get(
    f"{BASE_URL}/api/grep",
    params={"pattern": "Python"},
    headers=headers
)
print(response.json())
```

### Java with SandboxBackend

```java
import io.deepagents.backends.SandboxBackend;
import io.deepagents.backends.BackendProtocol;

public class FileServerExample {
    public static void main(String[] args) throws Exception {
        // Connect to dockerized FileServer
        BackendProtocol backend = new SandboxBackend(
            "http://localhost:8080",
            "your-api-key-here"  // Use actual key from logs
        );
        
        // Write a file
        backend.write("/example.txt", "Hello from Java!");
        
        // Read it back
        String content = backend.read("/example.txt", 0, 100);
        System.out.println(content);
        
        // List directory
        var files = backend.ls("/");
        files.forEach(file -> 
            System.out.println(file.path() + " - " + file.size() + " bytes")
        );
        
        // Search for pattern
        var matches = backend.grep("Hello", "/", null);
        matches.forEach(match -> 
            System.out.println(match.path() + ":" + match.line() + " - " + match.text())
        );
    }
}
```

### Shell Scripts

```bash
#!/bin/bash

# Configuration
BASE_URL="http://localhost:8080"
API_KEY="your-api-key-here"

# Helper function for authenticated requests
api_get() {
    curl -s -H "X-API-Key: $API_KEY" "$BASE_URL$1"
}

api_post() {
    curl -s -X POST -H "Content-Type: application/json" \
         -H "X-API-Key: $API_KEY" -d "$2" "$BASE_URL$1"
}

# Health check
echo "Health check:"
curl -s "$BASE_URL/health"
echo

# Write file
echo "Writing file..."
api_post "/api/write" '{"file_path": "/script-test.txt", "content": "Created by shell script"}'
echo

# Read file
echo "Reading file:"
api_get "/api/read?file_path=/script-test.txt"
echo

# List files
echo "Listing files:"
api_get "/api/ls?path=/"
echo

# Search
echo "Searching for 'script':"
api_get "/api/grep?pattern=script&path=/"
echo
```

### Node.js Client

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8080';
const API_KEY = 'your-api-key-here';

const client = axios.create({
    baseURL: BASE_URL,
    headers: { 'X-API-Key': API_KEY }
});

async function main() {
    // Write file
    await client.post('/api/write', {
        file_path: '/nodejs-test.txt',
        content: 'Hello from Node.js!'
    });
    console.log('File written');

    // Read file
    const response = await client.get('/api/read', {
        params: { file_path: '/nodejs-test.txt' }
    });
    console.log('File content:', response.data.content);

    // List files
    const files = await client.get('/api/ls', {
        params: { path: '/' }
    });
    console.log('Files:', files.data.files);

    // Search
    const matches = await client.get('/api/grep', {
        params: { pattern: 'Node', path: '/' }
    });
    console.log('Matches:', matches.data.matches);
}

main().catch(console.error);
```

## Advanced Examples

### Using with Docker Network

Create a custom network for inter-container communication:

```bash
# Create network
docker network create myapp-network

# Run FileServer on the network
docker run -d \
  --name fileserver \
  --network myapp-network \
  -e SERVER_TYPE=fastapi \
  -e API_KEY=secret-key \
  deepagents-fileserver

# Run your app on the same network
docker run -d \
  --name myapp \
  --network myapp-network \
  -e FILESERVER_URL=http://fileserver:8080 \
  -e FILESERVER_API_KEY=secret-key \
  myapp:latest
```

From `myapp`, access the FileServer at `http://fileserver:8080`.

### Multi-Instance Setup

Run multiple FileServer instances for different purposes:

```yaml
# docker-compose.yml
version: '3.8'

services:
  fileserver-prod:
    image: deepagents-fileserver
    ports:
      - "8080:8080"
    volumes:
      - ./prod-data:/data
    environment:
      - API_KEY=${PROD_API_KEY}
  
  fileserver-test:
    image: deepagents-fileserver
    ports:
      - "8081:8080"
    volumes:
      - ./test-data:/data
    environment:
      - API_KEY=${TEST_API_KEY}
  
  fileserver-dev:
    image: deepagents-fileserver
    ports:
      - "8082:8080"
    volumes:
      - ./dev-data:/data
    environment:
      - API_KEY=${DEV_API_KEY}
```

### With Reverse Proxy (nginx)

```yaml
# docker-compose.yml
version: '3.8'

services:
  fileserver:
    image: deepagents-fileserver
    expose:
      - 8080
    environment:
      - API_KEY=${API_KEY}
    networks:
      - internal

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - fileserver
    networks:
      - internal

networks:
  internal:
```

```nginx
# nginx.conf
server {
    listen 80;
    server_name fileserver.example.com;
    
    location / {
        proxy_pass http://fileserver:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test FileServer

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      fileserver:
        image: deepagents-fileserver:latest
        ports:
          - 8080:8080
        env:
          API_KEY: test-key
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Test FileServer
        run: |
          curl -H "X-API-Key: test-key" \
            -X POST http://localhost:8080/api/write \
            -H "Content-Type: application/json" \
            -d '{"file_path": "/test.txt", "content": "CI test"}'
          
          curl -H "X-API-Key: test-key" \
            "http://localhost:8080/api/read?file_path=/test.txt"
```

## Troubleshooting Examples

### Check if Server is Running

```bash
# Check container status
docker ps | grep fileserver

# Check health
docker inspect --format='{{.State.Health.Status}}' deepagents-fileserver-fastapi

# View logs
docker compose logs -f fileserver-fastapi
```

### Test Connection

```bash
# Basic health check
curl http://localhost:8080/health

# Test with wrong API key (should fail)
curl -H "X-API-Key: wrong-key" http://localhost:8080/api/ls

# Test with correct API key
curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/ls
```

### Debug Inside Container

```bash
# Get a shell inside the container
docker exec -it deepagents-fileserver-fastapi sh

# Check filesystem
ls -la /data

# Check processes
ps aux

# Test locally
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/health').read())"

# Exit
exit
```

### View Detailed Logs

```bash
# All logs
docker compose logs fileserver-fastapi

# Follow logs
docker compose logs -f fileserver-fastapi

# Last 100 lines
docker compose logs --tail=100 fileserver-fastapi

# Logs with timestamps
docker compose logs -t fileserver-fastapi
```

## Performance Testing

### Load Test with curl

```bash
#!/bin/bash
# Simple load test

API_KEY="your-api-key"

for i in {1..100}; do
    curl -s -H "X-API-Key: $API_KEY" \
      -X POST http://localhost:8080/api/write \
      -H "Content-Type: application/json" \
      -d "{\"file_path\": \"/test-$i.txt\", \"content\": \"Test file $i\"}" &
done

wait
echo "Load test completed"
```

### Benchmark with ab (Apache Bench)

```bash
# Install ab
sudo apt-get install apache2-utils

# Benchmark health endpoint (no auth)
ab -n 1000 -c 10 http://localhost:8080/health

# Benchmark with auth (requires ab-auth or custom script)
```

### Monitor Resource Usage

```bash
# Real-time stats
docker stats deepagents-fileserver-fastapi

# One-time stats
docker stats --no-stream deepagents-fileserver-fastapi

# Memory usage
docker exec deepagents-fileserver-fastapi \
  ps aux | grep python
```

## Integration Patterns

### Microservices Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Web App   │────▶│ API Gateway  │────▶│ FileServer  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Database   │
                    └──────────────┘
```

### Event-Driven Architecture

```
┌──────────┐        ┌──────────────┐        ┌─────────────┐
│ Producer │───────▶│ Message Bus  │───────▶│  Consumer   │
└──────────┘        └──────────────┘        └─────────────┘
                                                    │
                                                    ▼
                                            ┌─────────────┐
                                            │ FileServer  │
                                            └─────────────┘
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: Service
metadata:
  name: fileserver
spec:
  selector:
    app: fileserver
  ports:
    - port: 8080
      targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fileserver
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fileserver
  template:
    metadata:
      labels:
        app: fileserver
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

## See Also

- [DOCKER.md](DOCKER.md) - Complete Docker documentation
- [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) - Quick start guide
- [README.md](README.md) - API reference
- [FASTAPI_SECURITY_GUIDE.md](FASTAPI_SECURITY_GUIDE.md) - Security best practices
