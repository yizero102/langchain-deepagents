# DeepAgents Backends - Java Implementation

This is a Java implementation of the DeepAgents pluggable memory backends module, originally written in Python.

## Overview

This module provides pluggable backend implementations for storing and managing files in different locations:

- **StateBackend**: Stores files in memory (ephemeral, for testing or in-memory operations)
- **FilesystemBackend**: Reads and writes files directly to the filesystem
- **CompositeBackend**: Routes operations to different backends based on path prefixes

**Note**: The Python version includes a `StoreBackend` that integrates with LangGraph's BaseStore for persistent, cross-conversation storage. This is not implemented in Java as it requires Python-specific LangGraph framework integration. For persistent storage in Java, use `FilesystemBackend` or implement a custom backend.

## Features

- Protocol-based interface (`BackendProtocol`) for consistent API across backends
- File operations: read, write, edit, list, grep, glob
- Path resolution with security checks
- Line-numbered file reading with offset/limit support
- String replacement with occurrence validation
- Pattern matching and searching capabilities

## Building

This project uses Maven. To build:

```bash
cd libs/deepagents-backends-java
mvn clean compile
```

## Testing

Run tests with:

```bash
mvn test
```

## Usage

### StateBackend Example

```java
StateBackend backend = new StateBackend();

// Write a file
WriteResult writeResult = backend.write("/test.txt", "Hello World");

// Read a file
String content = backend.read("/test.txt");

// Edit a file
EditResult editResult = backend.edit("/test.txt", "World", "Java");

// List files
List<FileInfo> files = backend.lsInfo("/");

// Search with grep
List<GrepMatch> matches = (List<GrepMatch>) backend.grepRaw("Hello", "/", null);

// Glob search
List<FileInfo> txtFiles = backend.globInfo("*.txt", "/");
```

### FilesystemBackend Example

```java
Path rootDir = Paths.get("/path/to/root");
FilesystemBackend backend = new FilesystemBackend(rootDir, true, 10);

// Same operations as StateBackend
backend.write("/test.txt", "Content");
String content = backend.read("/test.txt");
```

### CompositeBackend Example

```java
StateBackend defaultBackend = new StateBackend();
StateBackend memoryBackend = new StateBackend();

Map<String, BackendProtocol> routes = new HashMap<>();
routes.put("/memory/", memoryBackend);

CompositeBackend composite = new CompositeBackend(defaultBackend, routes);

// Files under /memory/ go to memoryBackend
composite.write("/memory/file.txt", "In memory");

// Other files go to defaultBackend
composite.write("/file.txt", "In default");
```

## Protocol Interface

The `BackendProtocol` interface defines:

```java
public interface BackendProtocol {
    List<FileInfo> lsInfo(String path);
    String read(String filePath, int offset, int limit);
    Object grepRaw(String pattern, String path, String glob);
    List<FileInfo> globInfo(String pattern, String path);
    WriteResult write(String filePath, String content);
    EditResult edit(String filePath, String oldString, String newString, boolean replaceAll);
}
```

## Comparison with Python Version

This Java implementation maintains functional parity with the Python version while adapting to Java idioms:

| Feature | Python | Java |
|---------|--------|------|
| Interface | Protocol (duck typing) | Interface (explicit) |
| Data classes | TypedDict, dataclass | POJO classes |
| Error handling | Return error strings | Return Result objects with error field |
| Type system | Dynamic with type hints | Static typing |
| Collections | dict, list | Map, List |
| File I/O | pathlib.Path | java.nio.file.Path |

## Requirements

- Java 17 or later
- Maven 3.6 or later

## License

Same as the parent project.
