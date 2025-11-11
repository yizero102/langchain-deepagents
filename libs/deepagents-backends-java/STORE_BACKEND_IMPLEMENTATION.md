# StoreBackend Java Implementation

## Overview

This document describes the Java implementation of the StoreBackend, which provides a persistent storage backend for the DeepAgents framework. The implementation is based on the Python version and maintains functional parity.

## Components

### 1. Store Interface (`com.deepagents.backends.store.Store`)

The `Store` interface defines the contract for persistent key-value storage operations:

```java
public interface Store {
    Item get(String[] namespace, String key);
    void put(String[] namespace, String key, Map<String, Object> value);
    List<Item> search(String[] namespacePrefix, Map<String, Object> filter, int limit, int offset);
}
```

This interface is modeled after LangGraph's `BaseStore` class in Python.

### 2. Item Class (`com.deepagents.backends.store.Item`)

The `Item` class represents a stored item with metadata:

- `value`: Map containing the file data (content, created_at, modified_at)
- `key`: Unique identifier (file path)
- `namespace`: Hierarchical path tuple for organization
- `createdAt`: Timestamp of item creation
- `updatedAt`: Timestamp of last update

### 3. InMemoryStore Implementation (`com.deepagents.backends.store.InMemoryStore`)

A concrete implementation of the `Store` interface that keeps data in memory. This is used primarily for testing and mirrors Python's `InMemoryStore`.

Features:
- Namespace-based organization using String arrays
- Filter-based search capabilities
- Pagination support for large result sets

### 4. StoreBackend (`com.deepagents.backends.impl.StoreBackend`)

The main backend implementation that uses a `Store` instance for file operations.

Key methods:
- `lsInfo(String path)`: List files and directories (non-recursive)
- `read(String filePath, int offset, int limit)`: Read file content with line numbers
- `write(String filePath, String content)`: Create new file
- `edit(String filePath, String oldString, String newString, boolean replaceAll)`: Edit file
- `grepRaw(String pattern, String path, String glob)`: Search file contents
- `globInfo(String pattern, String path)`: Find files by glob pattern

## Implementation Details

### Namespace Handling

The backend uses a namespace array (default: `["filesystem"]`) to organize items in the store. This allows for:
- Multi-tenant isolation (e.g., `["assistant_id", "filesystem"]`)
- Hierarchical organization
- Consistent storage across threads

### File Data Conversion

Files are stored as Items with a value map containing:
```java
{
    "content": List<String>,      // File lines
    "created_at": String,          // ISO timestamp
    "modified_at": String          // ISO timestamp
}
```

The backend handles conversion between FileData and Store Item format.

### Search and Pagination

The `searchStorePaginated` method automatically handles pagination to retrieve all items:
- Default page size: 100 items
- Continues until no more results or page size not met
- Prevents memory issues with large datasets

### Directory Listing

The `lsInfo` method implements non-recursive directory listing:
1. Retrieves all items with matching path prefix
2. Identifies subdirectories by analyzing relative paths
3. Returns both files and directories (with trailing /)
4. Handles trailing slash normalization

## Test Coverage

The implementation includes comprehensive tests (`StoreBackendTest.java`):

1. **testStoreBackendCrudAndSearch**: Tests create, read, update, delete operations plus grep and glob
2. **testStoreBackendLsNestedDirectories**: Tests directory listing with nested structures
3. **testStoreBackendLsTrailingSlash**: Tests path normalization with/without trailing slashes
4. **testStoreBackendWriteExisting**: Tests error handling for duplicate writes
5. **testStoreBackendReadNonexistent**: Tests error handling for missing files
6. **testStoreBackendEditNonexistent**: Tests error handling for editing non-existent files

All tests maintain parity with the Python test suite.

## Comparison with Python Implementation

### Similarities
- Same interface methods and signatures
- Identical file data format
- Same namespace organization
- Equivalent search and pagination logic
- Matching glob pattern behavior

### Differences
- Java uses String arrays for namespaces instead of Python tuples
- Java uses Instant for timestamps instead of Python datetime
- InMemoryStore uses HashMap instead of Python defaultdict
- Error handling uses return values instead of exceptions where appropriate

## Usage Example

```java
// Create a store instance
Store store = new InMemoryStore();

// Create backend with default namespace
StoreBackend backend = new StoreBackend(store);

// Or with custom namespace
StoreBackend backend = new StoreBackend(store, new String[]{"user123", "filesystem"});

// Write a file
WriteResult result = backend.write("/docs/readme.md", "# Hello World");

// Read the file
String content = backend.read("/docs/readme.md");

// Edit the file
EditResult editResult = backend.edit("/docs/readme.md", "Hello", "Hi", false);

// List directory
List<FileInfo> files = backend.lsInfo("/docs/");

// Search with grep
List<GrepMatch> matches = (List<GrepMatch>) backend.grepRaw("World", "/", null);

// Find files with glob
List<FileInfo> mdFiles = backend.globInfo("**/*.md", "/");
```

## Glob Pattern Fix

During implementation, we discovered and fixed an issue in the `BackendUtils.matchesGlobPattern` method:

**Problem**: The pattern `*.md` was matching files in subdirectories (e.g., `/docs/readme.md`)

**Fix**: Updated the logic to respect standard glob semantics:
- Patterns without `/` only match files in the current directory
- Use `**/` for recursive matching
- Patterns with `/` must match the exact path structure

This ensures consistency with Python's `wcglob` library behavior.

## Future Enhancements

Possible improvements for production use:
1. Add TTL (time-to-live) support for item expiration
2. Implement vector search capabilities for semantic queries
3. Add database-backed Store implementations (PostgreSQL, etc.)
4. Support for async operations
5. Compression for large file content
6. Transaction support for atomic multi-file operations
