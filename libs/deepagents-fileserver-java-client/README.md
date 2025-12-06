# DeepAgents FileServer Java Client

A comprehensive Java client library for the DeepAgents FileServer HTTP API.

## Features

- **Full API Coverage**: Supports all BackendProtocol operations (read, write, edit, ls, grep, glob)
- **Type-Safe**: Strongly typed request/response models using Gson
- **Authentication Support**: Optional API key authentication
- **Configurable**: Customizable timeouts and connection settings
- **Zero External Dependencies**: Uses only Java standard library and Gson
- **Thread-Safe**: Can be used safely across multiple threads

## Requirements

- Java 17 or higher
- Maven 3.6 or higher (for building)

## Building

```bash
mvn clean install
```

## Usage

### Basic Usage

```java
import com.deepagents.fileserver.client.FileServerClient;
import com.deepagents.fileserver.client.FileInfo;
import com.deepagents.fileserver.client.WriteResponse;

// Create client (no authentication)
try (FileServerClient client = new FileServerClient("http://localhost:8080")) {
    
    // Health check
    boolean healthy = client.healthCheck();
    
    // Write a file
    WriteResponse response = client.writeFile("test.txt", "Hello, World!");
    
    // Read a file
    String content = client.readFile("test.txt");
    
    // Edit a file
    EditResponse editResponse = client.editFile("test.txt", "World", "Java");
    
    // List directory
    List<FileInfo> files = client.listDirectory(".");
    
    // Search with grep
    List<GrepMatch> matches = client.grep("pattern");
    
    // Find files with glob
    List<FileInfo> matchedFiles = client.glob("*.txt");
}
```

### With Authentication

```java
// Create client with API key
try (FileServerClient client = new FileServerClient(
    "http://localhost:8080",
    "your-api-key-here"
)) {
    // All operations will include the API key
    String content = client.readFile("secure-file.txt");
}
```

### Custom Timeouts

```java
// Create client with custom timeouts
try (FileServerClient client = new FileServerClient(
    "http://localhost:8080",
    "api-key",
    10000,  // Connect timeout (ms)
    60000   // Read timeout (ms)
)) {
    // Operations with custom timeouts
}
```

## API Methods

### Health Check

```java
boolean healthy = client.healthCheck();
```

### Write File

```java
WriteResponse response = client.writeFile("path/to/file.txt", "content");
if (response.getError() == null) {
    System.out.println("File created at: " + response.getPath());
}
```

### Read File

```java
// Read entire file (up to default limit)
String content = client.readFile("path/to/file.txt");

// Read with pagination
String content = client.readFile("path/to/file.txt", offset, limit);
```

### Edit File

```java
// Replace first occurrence
EditResponse response = client.editFile(
    "path/to/file.txt",
    "old text",
    "new text"
);

// Replace all occurrences
EditResponse response = client.editFile(
    "path/to/file.txt",
    "old text",
    "new text",
    true  // replaceAll
);
```

### List Directory

```java
List<FileInfo> files = client.listDirectory("path/to/directory");
for (FileInfo file : files) {
    System.out.println(file.getPath() + " - " + 
                       (file.isDir() ? "DIR" : "FILE"));
}
```

### Grep (Search)

```java
// Simple search
List<GrepMatch> matches = client.grep("search pattern");

// Search with path and glob filter
List<GrepMatch> matches = client.grep(
    "pattern",
    "/path/to/search",
    "*.java"  // Only search .java files
);

for (GrepMatch match : matches) {
    System.out.println(match.getPath() + ":" + 
                       match.getLine() + " - " + 
                       match.getText());
}
```

### Glob (Pattern Matching)

```java
// Find all .txt files
List<FileInfo> files = client.glob("*.txt");

// Find in specific directory
List<FileInfo> files = client.glob("*.java", "/path/to/src");
```

## Response Models

### FileInfo

```java
class FileInfo {
    String path;          // File or directory path
    boolean isDir;        // true if directory
    Integer size;         // File size in bytes (null for dirs)
    String modifiedAt;    // ISO timestamp of last modification
}
```

### WriteResponse

```java
class WriteResponse {
    String error;   // Error message (null if success)
    String path;    // Created file path (null if error)
}
```

### EditResponse

```java
class EditResponse {
    String error;          // Error message (null if success)
    String path;           // Edited file path (null if error)
    Integer occurrences;   // Number of replacements made
}
```

### GrepMatch

```java
class GrepMatch {
    String path;    // File path containing match
    int line;       // Line number (1-indexed)
    String text;    // Line text containing match
}
```

## Error Handling

The client throws `IOException` for:
- Network errors
- HTTP errors (4xx, 5xx status codes)
- Invalid responses

```java
try {
    String content = client.readFile("missing.txt");
} catch (IOException e) {
    System.err.println("Error reading file: " + e.getMessage());
}
```

## Testing

Run the test suite:

```bash
mvn test
```

**Note**: Tests require a running FileServer instance at http://localhost:8080

## Thread Safety

The `FileServerClient` is thread-safe and can be shared across multiple threads. However, for optimal performance in multi-threaded environments, consider creating a client pool.

## Performance

- Lightweight: Minimal memory footprint
- Fast: Direct HTTP connections without overhead
- Efficient: Reuses connections when possible

## License

MIT License - See parent project LICENSE file for details

## Contributing

Contributions are welcome! Please ensure:
- All tests pass: `mvn test`
- Code follows Java conventions
- New features include corresponding tests

## Related Projects

- [DeepAgents FileServer](../deepagents-fileserver) - Python FastAPI server
- [DeepAgents Java Backends](../deepagents-backends-java) - Java backend implementations
