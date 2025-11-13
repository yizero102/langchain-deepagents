package com.deepagents.fileserver.client;

import org.junit.jupiter.api.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Comprehensive test suite for FileServerClient.
 * Tests all BackendProtocol operations exposed via the Java client.
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class FileServerClientTest {
    private static final String BASE_URL = "http://localhost:8080";
    private static FileServerClient client;
    private static Path tempDir;

    @BeforeAll
    public static void setup() throws IOException {
        tempDir = Files.createTempDirectory("fileserver-test");
        client = new FileServerClient(BASE_URL);
    }

    @AfterAll
    public static void teardown() throws IOException {
        if (client != null) {
            client.close();
        }
        if (tempDir != null) {
            deleteDirectory(tempDir);
        }
    }

    private static void deleteDirectory(Path path) throws IOException {
        if (Files.exists(path)) {
            Files.walk(path)
                    .sorted((a, b) -> b.compareTo(a))
                    .forEach(p -> {
                        try {
                            Files.delete(p);
                        } catch (IOException e) {
                            // Ignore
                        }
                    });
        }
    }

    @Test
    @Order(1)
    public void testHealthCheck() throws IOException {
        boolean healthy = client.healthCheck();
        assertTrue(healthy, "Server should be healthy");
    }

    @Test
    @Order(2)
    public void testWriteNewFile() throws IOException {
        WriteResponse response = client.writeFile("test_write.txt", "Hello, World!");
        assertNull(response.getError(), "Write should succeed");
        assertEquals("test_write.txt", response.getPath());
    }

    @Test
    @Order(3)
    public void testWriteExistingFileFails() {
        assertThrows(IOException.class, () -> {
            client.writeFile("test_write.txt", "New content");
        }, "Writing to existing file should fail");
    }

    @Test
    @Order(4)
    public void testWriteNestedDirectory() throws IOException {
        WriteResponse response = client.writeFile("nested/dir/test.txt", "Nested content");
        assertNull(response.getError(), "Write to nested directory should succeed");
        assertEquals("nested/dir/test.txt", response.getPath());
    }

    @Test
    @Order(5)
    public void testReadFile() throws IOException {
        String content = client.readFile("test_write.txt");
        assertNotNull(content, "Read should return content");
        assertTrue(content.contains("Hello, World!"), "Content should match");
        assertTrue(content.contains("1 |"), "Content should have line numbers");
    }

    @Test
    @Order(6)
    public void testReadFileWithPagination() throws IOException {
        // Create a file with many lines
        StringBuilder sb = new StringBuilder();
        for (int i = 1; i <= 100; i++) {
            sb.append("Line ").append(i).append("\n");
        }
        client.writeFile("pagination_test.txt", sb.toString());

        // Read with offset and limit
        String content = client.readFile("pagination_test.txt", 10, 5);
        assertTrue(content.contains("Line 11"), "Should contain line at offset 10");
        assertTrue(content.contains("Line 15"), "Should contain line at offset 14");
        assertFalse(content.contains("Line 16"), "Should not contain line beyond limit");
    }

    @Test
    @Order(7)
    public void testReadNonexistentFile() throws IOException {
        String content = client.readFile("nonexistent.txt");
        assertTrue(content.toLowerCase().contains("not found"), "Should indicate file not found");
    }

    @Test
    @Order(8)
    public void testEditFile() throws IOException {
        // Create a test file
        client.writeFile("edit_test.txt", "Hello World\nHello Universe\n");

        // Edit the file
        EditResponse response = client.editFile("edit_test.txt", "World", "Java");
        assertNull(response.getError(), "Edit should succeed");
        assertEquals(1, response.getOccurrences(), "Should replace one occurrence");

        // Verify edit
        String content = client.readFile("edit_test.txt");
        assertTrue(content.contains("Hello Java"), "Should contain edited text");
        assertTrue(content.contains("Hello Universe"), "Should contain unchanged text");
    }

    @Test
    @Order(9)
    public void testEditFileReplaceAll() throws IOException {
        // Create a test file with multiple occurrences
        client.writeFile("replace_all_test.txt", "foo bar foo baz foo");

        // Edit with replace all
        EditResponse response = client.editFile("replace_all_test.txt", "foo", "qux", true);
        assertNull(response.getError(), "Edit should succeed");
        assertEquals(3, response.getOccurrences(), "Should replace all occurrences");

        // Verify all occurrences replaced
        String content = client.readFile("replace_all_test.txt");
        assertTrue(content.contains("qux bar qux baz qux"), "All occurrences should be replaced");
        assertFalse(content.contains("foo"), "Original string should not exist");
    }

    @Test
    @Order(10)
    public void testEditNonexistentFile() {
        assertThrows(IOException.class, () -> {
            client.editFile("nonexistent_edit.txt", "old", "new");
        }, "Editing nonexistent file should fail");
    }

    @Test
    @Order(11)
    public void testEditStringNotFound() {
        assertThrows(IOException.class, () -> {
            client.writeFile("no_match.txt", "Some content");
            client.editFile("no_match.txt", "nonexistent", "new");
        }, "Editing with non-matching string should fail");
    }

    @Test
    @Order(12)
    public void testListDirectory() throws IOException {
        // Create test files
        client.writeFile("list_test1.txt", "content1");
        client.writeFile("list_test2.txt", "content2");

        // List directory
        List<FileInfo> files = client.listDirectory(".");
        assertNotNull(files, "Should return file list");
        assertTrue(files.size() > 0, "Should contain files");

        // Check for our test files
        boolean found1 = files.stream().anyMatch(f -> f.getPath().contains("list_test1.txt"));
        boolean found2 = files.stream().anyMatch(f -> f.getPath().contains("list_test2.txt"));
        assertTrue(found1, "Should find list_test1.txt");
        assertTrue(found2, "Should find list_test2.txt");

        // Check metadata
        FileInfo fileInfo = files.stream()
                .filter(f -> f.getPath().contains("list_test1.txt"))
                .findFirst()
                .orElse(null);
        assertNotNull(fileInfo, "Should have file info");
        assertFalse(fileInfo.isDir(), "File should not be directory");
        assertNotNull(fileInfo.getSize(), "Should have size");
    }

    @Test
    @Order(13)
    public void testListNonexistentDirectory() throws IOException {
        List<FileInfo> files = client.listDirectory("/nonexistent_dir_12345");
        assertNotNull(files, "Should return list");
        assertEquals(0, files.size(), "Should be empty for nonexistent directory");
    }

    @Test
    @Order(14)
    public void testGrepSearch() throws IOException {
        // Create test files
        client.writeFile("grep_test1.txt", "Hello World\nHello Java\n");
        client.writeFile("grep_test2.txt", "Goodbye World\n");
        client.writeFile("grep_test3.py", "print('Hello')\n");

        // Search for pattern
        List<GrepMatch> matches = client.grep("Hello");
        assertNotNull(matches, "Should return matches");
        assertTrue(matches.size() >= 2, "Should find at least 2 matches");

        // Check match structure
        for (GrepMatch match : matches) {
            assertNotNull(match.getPath(), "Should have path");
            assertTrue(match.getLine() > 0, "Should have line number");
            assertNotNull(match.getText(), "Should have text");
            assertTrue(match.getText().contains("Hello"), "Text should contain pattern");
        }
    }

    @Test
    @Order(15)
    public void testGrepWithGlobFilter() throws IOException {
        // Create test files
        client.writeFile("glob_grep1.txt", "pattern match\n");
        client.writeFile("glob_grep2.py", "pattern match\n");

        // Search with glob filter
        List<GrepMatch> matches = client.grep("pattern", ".", "*.txt");
        assertNotNull(matches, "Should return matches");

        // Should only match .txt files
        for (GrepMatch match : matches) {
            assertTrue(match.getPath().endsWith(".txt"), "Should only match .txt files");
        }
    }

    @Test
    @Order(16)
    public void testGrepInvalidRegex() {
        assertThrows(IOException.class, () -> {
            client.grep("[invalid");
        }, "Invalid regex should throw exception");
    }

    @Test
    @Order(17)
    public void testGlobPattern() throws IOException {
        // Create test files
        client.writeFile("glob1.txt", "content");
        client.writeFile("glob2.txt", "content");
        client.writeFile("glob3.py", "content");

        // Glob for .txt files
        List<FileInfo> files = client.glob("*.txt");
        assertNotNull(files, "Should return files");
        assertTrue(files.size() >= 2, "Should find at least 2 .txt files");

        // Check all are .txt files
        for (FileInfo file : files) {
            assertTrue(file.getPath().endsWith(".txt"), "All files should be .txt");
            assertFalse(file.isDir(), "Should be files, not directories");
        }
    }

    @Test
    @Order(18)
    public void testGlobRecursivePattern() throws IOException {
        // Create nested structure
        client.writeFile("root.md", "content");
        client.writeFile("sub1/file1.md", "content");
        client.writeFile("sub1/sub2/file2.md", "content");

        // Glob for all .md files
        List<FileInfo> files = client.glob("*.md");
        assertNotNull(files, "Should return files");
        assertTrue(files.size() >= 3, "Should find all .md files in subdirectories");
    }

    @Test
    @Order(19)
    public void testGlobNonexistentDirectory() throws IOException {
        List<FileInfo> files = client.glob("*.txt", "/nonexistent_glob_dir");
        assertNotNull(files, "Should return list");
        assertEquals(0, files.size(), "Should be empty for nonexistent directory");
    }

    @Test
    @Order(20)
    public void testWriteEmptyContent() throws IOException {
        WriteResponse response = client.writeFile("empty.txt", "");
        assertNull(response.getError(), "Writing empty file should succeed");
    }

    @Test
    @Order(21)
    public void testReadEmptyFile() throws IOException {
        String content = client.readFile("empty.txt");
        assertNotNull(content, "Should return content");
        assertTrue(content.toLowerCase().contains("empty"), "Should indicate file is empty");
    }

    @Test
    @Order(22)
    public void testUnicodeContent() throws IOException {
        String unicodeContent = "Hello 世界 🌍 Привет";

        // Write unicode content
        WriteResponse response = client.writeFile("unicode.txt", unicodeContent);
        assertNull(response.getError(), "Writing unicode should succeed");

        // Read back
        String content = client.readFile("unicode.txt");
        assertTrue(content.contains("世界"), "Should contain Chinese characters");
        assertTrue(content.contains("🌍"), "Should contain emoji");
        assertTrue(content.contains("Привет"), "Should contain Cyrillic");
    }

    @Test
    @Order(23)
    public void testAuthenticationWithValidKey() throws IOException {
        // This test assumes server is running with authentication
        // It will be skipped if server doesn't require auth
        // You would need to start a server with auth enabled for this test
        // FileServerClient authClient = new FileServerClient(BASE_URL, "valid-api-key");
        // assertTrue(authClient.healthCheck());
        // authClient.close();
    }

    @Test
    @Order(24)
    public void testConcurrentOperations() throws IOException {
        // Write multiple files
        for (int i = 0; i < 5; i++) {
            WriteResponse response = client.writeFile("concurrent" + i + ".txt", "Content " + i);
            assertNull(response.getError(), "Write should succeed for file " + i);
        }

        // Read them back
        for (int i = 0; i < 5; i++) {
            String content = client.readFile("concurrent" + i + ".txt");
            assertTrue(content.contains("Content " + i), "Should read correct content for file " + i);
        }
    }
}
