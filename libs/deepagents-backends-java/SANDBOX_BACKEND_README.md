# SandboxBackend Implementation

## Overview

The `SandboxBackend` is a Java implementation of the `BackendProtocol` interface that communicates with a remote FileServer over HTTP. This enables sandboxed file operations where the actual filesystem operations are performed by a separate server process, providing isolation and security benefits.

## Features

- **Remote File Operations**: All file operations are performed via HTTP API calls to a FileServer
- **Full BackendProtocol Support**: Implements all operations (read, write, edit, ls, grep, glob)
- **Authentication Support**: Optional API key authentication for secure communication
- **Error Handling**: Graceful error handling with informative error messages
- **Network Resilience**: Configurable timeouts and proper connection management

## Architecture

```
┌─────────────────────┐         HTTP/REST API        ┌─────────────────────┐
│  SandboxBackend     │ ────────────────────────────> │   FileServer        │
│  (Java Client)      │ <──────────────────────────── │   (Python Server)   │
└─────────────────────┘                               └─────────────────────┘
         │                                                       │
         │ Implements                                            │ Accesses
         │ BackendProtocol                                       │ Filesystem
         ▼                                                       ▼
┌─────────────────────┐                               ┌─────────────────────┐
│   Application       │                               │   Actual Files      │
│   Code              │                               │   on Disk           │
└─────────────────────┘                               └─────────────────────┘
```

## Usage

### Basic Usage

```java
import com.deepagents.backends.impl.SandboxBackend;
import com.deepagents.backends.protocol.*;

// Create backend with server URL
SandboxBackend backend = new SandboxBackend("http://localhost:8080");

// Write a file
WriteResult writeResult = backend.write("test.txt", "Hello World");
if (writeResult.isSuccess()) {
    System.out.println("File written: " + writeResult.getPath());
}

// Read a file
String content = backend.read("test.txt");
System.out.println(content);

// Edit a file
EditResult editResult = backend.edit("test.txt", "World", "Java");
if (editResult.isSuccess()) {
    System.out.println("Replaced " + editResult.getOccurrences() + " occurrence(s)");
}

// List directory
List<FileInfo> files = backend.lsInfo(".");
for (FileInfo info : files) {
    System.out.println(info.getPath() + " (dir: " + info.isDir() + ")");
}

// Search files
Object grepResult = backend.grepRaw("pattern", ".", null);
if (grepResult instanceof List) {
    @SuppressWarnings("unchecked")
    List<GrepMatch> matches = (List<GrepMatch>) grepResult;
    for (GrepMatch match : matches) {
        System.out.println(match.getPath() + ":" + match.getLine() + " - " + match.getText());
    }
}

// Glob pattern matching
List<FileInfo> txtFiles = backend.globInfo("*.txt", ".");
```

### With API Key Authentication

```java
// Create backend with API key
SandboxBackend backend = new SandboxBackend("http://localhost:8080", "your-api-key");

// All operations will automatically include the API key in X-API-Key header
WriteResult result = backend.write("secure.txt", "Secure content");
```

## API Mapping

The SandboxBackend translates BackendProtocol operations to FileServer HTTP endpoints:

| BackendProtocol Method | HTTP Endpoint | Method |
|------------------------|---------------|--------|
| `lsInfo(path)` | `/api/ls?path=...` | GET |
| `read(filePath, offset, limit)` | `/api/read?file_path=...&offset=...&limit=...` | GET |
| `write(filePath, content)` | `/api/write` | POST |
| `edit(filePath, oldString, newString, replaceAll)` | `/api/edit` | POST |
| `grepRaw(pattern, path, glob)` | `/api/grep?pattern=...&path=...&glob=...` | GET |
| `globInfo(pattern, path)` | `/api/glob?pattern=...&path=...` | GET |

## Testing

The SandboxBackend includes comprehensive test coverage (26 tests) that verify:

- ✅ Basic file operations (read, write, edit)
- ✅ Directory listing and nested directories
- ✅ Search operations (grep with and without glob)
- ✅ Glob pattern matching (simple and recursive)
- ✅ Unicode content support
- ✅ Large file handling
- ✅ Multiline content editing
- ✅ Error handling (non-existent files, network failures)
- ✅ Deep nested paths
- ✅ Special characters in filenames
- ✅ Edge cases (empty files, no matches, etc.)

### Running Tests

```bash
cd libs/deepagents-backends-java
mvn test -Dtest=SandboxBackendTest
```

**Note**: Tests automatically start a temporary FileServer instance on port 8765. Make sure this port is available.

## Implementation Details

### HTTP Client

The SandboxBackend uses Java's built-in `java.net.http.HttpClient` (Java 11+) for HTTP communication, requiring no external dependencies beyond those already used by the project (Gson for JSON parsing).

### Timeouts

- **Connection Timeout**: 10 seconds
- **Request Timeout**: 30 seconds

### Error Handling

All methods handle errors gracefully:

- Network failures return error messages in the response
- Server errors (4xx, 5xx) are caught and wrapped in appropriate error responses
- JSON parsing errors are handled and reported

### Path Handling

- File paths should be relative (e.g., `"test.txt"`, `"dir/file.txt"`)
- Absolute paths starting with `/` may cause permission errors depending on server configuration
- The server resolves all paths relative to its root directory

## Performance

The SandboxBackend performance depends on:

1. **Network Latency**: HTTP overhead for each operation
2. **Server Performance**: FileServer processing time
3. **File Size**: Larger files take longer to transfer

For optimal performance:

- Use a local FileServer when possible
- Keep the FileServer close to the backend (same machine/network)
- Consider batching operations when appropriate

## Security Considerations

### Authentication

When using the FastAPI FileServer (recommended), always use API key authentication:

```java
SandboxBackend backend = new SandboxBackend(
    "http://localhost:8080",
    System.getenv("FILESERVER_API_KEY")  // Store API key securely
);
```

### HTTPS

For production use, deploy the FileServer behind HTTPS:

```java
SandboxBackend backend = new SandboxBackend(
    "https://fileserver.example.com",
    apiKey
);
```

### Path Traversal

The FileServer includes path traversal protection. The SandboxBackend relies on the server to enforce path restrictions.

## Comparison with Other Backends

| Feature | SandboxBackend | StateBackend | FilesystemBackend | CompositeBackend |
|---------|---------------|--------------|-------------------|------------------|
| **Storage** | Remote filesystem | In-memory | Local filesystem | Hybrid (multiple) |
| **Persistence** | ✅ Yes (server-side) | ❌ No | ✅ Yes | Depends on backends |
| **Network Required** | ✅ Yes | ❌ No | ❌ No | Depends on backends |
| **Isolation** | ✅ High (separate process) | ⚠️ Low | ⚠️ Low | Depends on backends |
| **Performance** | ⚠️ Moderate (network) | ✅ Fast | ✅ Fast | Depends on backends |
| **Use Case** | Sandboxed environments, distributed systems | Testing, temporary data | Local file access | Multiple storage locations |

## Troubleshooting

### Connection Refused

**Problem**: `Connection refused` or `Server did not start within expected time`

**Solutions**:
1. Ensure FileServer is running: `python -m fileserver.server /path/to/root 8080`
2. Check the port is correct and not blocked by firewall
3. Verify the URL is correct (http://localhost:8080)

### Permission Denied

**Problem**: `Permission denied` errors when writing files

**Solutions**:
1. Use relative paths instead of absolute paths (e.g., `"test.txt"` not `"/test.txt"`)
2. Ensure the FileServer root directory has appropriate permissions
3. Check that the FileServer user has write access to the target directory

### Timeout Errors

**Problem**: Operations timeout

**Solutions**:
1. Check network connectivity to the FileServer
2. Verify the FileServer is responsive: `curl http://localhost:8080/health`
3. For large files, the default 30-second timeout may need adjustment (requires code modification)

### JSON Parsing Errors

**Problem**: Unexpected JSON format errors

**Solutions**:
1. Ensure FileServer version is compatible
2. Check server logs for errors
3. Verify the FileServer is not returning HTML error pages instead of JSON

## Dependencies

The SandboxBackend requires:

- **Java 17+** (for HttpClient and modern features)
- **Gson 2.10.1+** (for JSON parsing)
- **JUnit 5.10.0+** (for testing only)

No additional dependencies are needed beyond those already in the project.

## Future Enhancements

Potential improvements for future versions:

1. **Retry Logic**: Automatic retry on transient failures
2. **Connection Pooling**: Reuse HTTP connections for better performance
3. **Async Operations**: Non-blocking async API for concurrent operations
4. **Caching**: Client-side caching for read operations
5. **Batch Operations**: Support for multiple operations in a single request
6. **Health Monitoring**: Periodic health checks and connection status
7. **Metrics**: Operation timing and success/failure tracking

## License

Same as the parent project (MIT License).

## Contributing

When contributing to SandboxBackend:

1. Ensure all existing tests pass: `mvn test`
2. Add tests for new functionality
3. Follow existing code style and patterns
4. Update this documentation for significant changes
5. Test with both standard and FastAPI FileServer implementations
