# Test Coverage Mapping: Python ↔ Java

This document maps each Python test to its corresponding Java test(s) and documents additional comprehensive tests added.

## StateBackend

### Python Tests → Java Tests Mapping

| Python Test | Java Test(s) | Status |
|------------|--------------|--------|
| `test_write_read_edit_ls_grep_glob_state_backend` | `testWriteAndRead`, `testEditFile`, `testLsInfo`, `testGrepRaw`, `testGlobInfo` | ✅ Covered + Enhanced |
| `test_state_backend_errors` | `testWriteExistingFile`, `testReadNonExistentFile`, `testEditNonExistentFile` | ✅ Covered |
| `test_state_backend_ls_nested_directories` | `testLsNestedDirectories` | ✅ Covered |
| `test_state_backend_ls_trailing_slash` | `testLsTrailingSlash` | ✅ Covered |
| `test_state_backend_intercept_large_tool_result` | N/A (middleware testing) | ⚠️ Not applicable to pure backend |

### Additional Java Tests (New)

1. `testEditWithMultipleOccurrences` - Tests error when multiple matches without replace_all
2. `testEditWithReplaceAll` - Tests replace_all functionality
3. `testReadWithOffsetAndLimit` - Tests pagination for large files
4. `testEmptyContent` - Tests empty file handling
5. `testGrepInvalidRegex` - Tests invalid regex pattern handling
6. `testEditStringNotFound` - Tests error when string not found
7. `testRecursiveGlob` - Tests **/ recursive glob patterns
8. `testGlobNoRecursion` - Tests non-recursive glob behavior
9. `testGrepWithGlob` - Tests grep with glob filtering
10. `testReadAndWriteUnicode` - Tests Unicode character handling
11. `testEditWithNewlines` - Tests multi-line content editing
12. `testDeepNestedDirectories` - Tests 5+ level nested directories
13. `testMultipleEdits` - Tests sequential edit operations
14. `testGlobWithMultipleExtensions` - Tests glob with various file types

**Total: 24 tests (Python: 5, New Java: 14)**

---

## FilesystemBackend

### Python Tests → Java Tests Mapping

| Python Test | Java Test(s) | Status |
|------------|--------------|--------|
| `test_filesystem_backend_normal_mode` | `testWriteAndRead`, `testNormalModeAbsolutePaths` | ✅ Covered |
| `test_filesystem_backend_virtual_mode` | All tests with `virtualMode=true` | ✅ Covered |
| `test_filesystem_backend_ls_nested_directories` | `testLsNestedDirectories` | ✅ Covered |
| `test_filesystem_backend_ls_normal_mode_nested` | `testLsNestedDirectories` (normal mode) | ✅ Covered |
| `test_filesystem_backend_ls_trailing_slash` | `testLsTrailingSlash` | ✅ Covered |
| `test_filesystem_backend_intercept_large_tool_result` | N/A (middleware testing) | ⚠️ Not applicable |

### Additional Java Tests (New)

1. `testEditFile` - Basic edit functionality
2. `testLsInfo` - Directory listing
3. `testGrepRaw` - Grep functionality
4. `testGlobInfo` - Glob pattern matching
5. `testNestedDirectories` - Nested path handling
6. `testPathTraversalPrevention` - Security testing
7. `testRecursiveGlob` - Recursive glob patterns
8. `testReadWithOffsetAndLimit` - Pagination testing
9. `testEditStringNotFound` - Error handling
10. `testEditWithMultipleOccurrences` - Multiple match handling
11. `testEditWithReplaceAll` - Replace all functionality
12. `testGrepWithGlob` - Combined grep and glob
13. `testUnicodeContent` - Unicode character support
14. `testEmptyFile` - Empty file handling
15. `testEditNonExistentFile` - Error case
16. `testGlobNoRecursion` - Non-recursive glob
17. `testGrepInvalidRegex` - Invalid pattern handling

**Total: 23 tests (Python: 6, New Java: 17)**

---

## StoreBackend

### Python Tests → Java Tests Mapping

| Python Test | Java Test(s) | Status |
|------------|--------------|--------|
| `test_store_backend_crud_and_search` | `testStoreBackendCrudAndSearch` | ✅ Covered |
| `test_store_backend_ls_nested_directories` | `testStoreBackendLsNestedDirectories` | ✅ Covered |
| `test_store_backend_ls_trailing_slash` | `testStoreBackendLsTrailingSlash` | ✅ Covered |
| `test_store_backend_intercept_large_tool_result` | N/A (middleware testing) | ⚠️ Not applicable |

### Additional Java Tests (New)

1. `testStoreBackendWriteExisting` - Duplicate write error
2. `testStoreBackendReadNonexistent` - Read missing file
3. `testStoreBackendEditNonexistent` - Edit missing file
4. `testStoreBackendEditStringNotFound` - Edit with no match
5. `testStoreBackendEditMultipleOccurrences` - Multiple matches
6. `testStoreBackendEditReplaceAll` - Replace all matches
7. `testStoreBackendGrepWithGlob` - Grep with glob filter
8. `testStoreBackendUnicode` - Unicode support
9. `testStoreBackendEmptyContent` - Empty file
10. `testStoreBackendGrepInvalidRegex` - Invalid regex
11. `testStoreBackendGlobNoRecursion` - Non-recursive glob
12. `testStoreBackendRecursiveGlob` - Recursive glob

**Total: 15 tests (Python: 4, New Java: 11)**

---

## CompositeBackend

### Python Tests → Java Tests Mapping

| Python Test | Java Test(s) | Status |
|------------|--------------|--------|
| `test_composite_state_backend_routes_and_search` | `testWriteToDefaultBackend`, `testWriteToRoutedBackend`, `testLsInfoRoot`, `testGrepAcrossBackends`, `testGlobAcrossBackends` | ✅ Covered |
| `test_composite_backend_filesystem_plus_store` | N/A | ⚠️ Uses mixed backends (can add if needed) |
| `test_composite_backend_store_to_store` | `testMultipleRoutes` (similar concept) | ✅ Covered |
| `test_composite_backend_multiple_routes` | `testMultipleRoutes` | ✅ Covered |
| `test_composite_backend_ls_nested_directories` | `testLsNestedDirectories` | ✅ Covered |
| `test_composite_backend_ls_multiple_routes_nested` | `testLsNestedDirectories`, `testMultipleRoutes` | ✅ Covered |
| `test_composite_backend_ls_trailing_slash` | `testLsTrailingSlash` | ✅ Covered |
| `test_composite_backend_intercept_large_tool_result` | N/A (middleware testing) | ⚠️ Not applicable |
| `test_composite_backend_intercept_large_tool_result_routed_to_store` | N/A (middleware testing) | ⚠️ Not applicable |

### Additional Java Tests (New)

1. `testLsInfoRoutedPath` - Route-specific listing
2. `testEditRoutedFile` - Edit in routed backend
3. `testEditStringNotFound` - Error handling
4. `testEditMultipleOccurrences` - Multiple match error
5. `testEditReplaceAll` - Replace all in composite
6. `testGrepInvalidRegex` - Invalid pattern
7. `testReadNonexistent` - Missing file
8. `testWriteToRoutedPathErrors` - Duplicate write
9. `testDeepNestedInRoutedBackend` - Deep nesting
10. `testGlobAcrossMultipleRoutes` - Multi-route glob
11. `testGrepSpecificRoute` - Route-specific grep
12. `testUnicodeInComposite` - Unicode support

**Total: 20 tests (Python: 9, New Java: 11)**

---

## Summary Statistics

| Backend | Python Tests | Java Tests | Coverage Ratio |
|---------|-------------|------------|----------------|
| StateBackend | 5 | 24 | 480% |
| FilesystemBackend | 6 | 23 | 383% |
| StoreBackend | 4 | 15 | 375% |
| CompositeBackend | 9 | 20 | 222% |
| **TOTAL** | **24** | **82** | **342%** |

## Test Categories

### Functional Tests (Core Operations)
- ✅ Read/Write/Edit operations
- ✅ ls_info (directory listing)
- ✅ grep (content search)
- ✅ glob (pattern matching)

### Edge Cases
- ✅ Empty files
- ✅ Unicode characters
- ✅ Very long files
- ✅ Deep nested directories
- ✅ Multiple sequential operations

### Error Handling
- ✅ Missing files
- ✅ Duplicate writes
- ✅ Invalid regex patterns
- ✅ String not found
- ✅ Multiple occurrences
- ✅ Path traversal attempts

### Advanced Features
- ✅ Offset/limit pagination
- ✅ Recursive glob (**/*)
- ✅ Non-recursive glob (*)
- ✅ Grep with glob filtering
- ✅ Replace all functionality
- ✅ Route-based composition

## Notes

1. **Middleware Tests**: The Python tests include middleware integration tests (large tool result interception). These are not replicated in Java backend tests as they test middleware behavior, not backend logic.

2. **Enhanced Coverage**: Java tests include significantly more edge cases and error scenarios to ensure robust production behavior.

3. **Unicode Support**: Java tests explicitly verify Unicode character handling, which is implicit in Python's string handling.

4. **Pattern Matching**: Both implementations follow standard glob semantics:
   - `*.txt` - matches only in current directory
   - `**/*.txt` - matches recursively in all subdirectories

5. **Error Messages**: Java tests verify error message content matches Python's error patterns for consistency.
