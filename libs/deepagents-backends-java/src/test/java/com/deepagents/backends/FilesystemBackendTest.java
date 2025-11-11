package com.deepagents.backends;

import com.deepagents.backends.impl.FilesystemBackend;
import com.deepagents.backends.protocol.*;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.*;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class FilesystemBackendTest {
    
    private Path tempDir;
    private FilesystemBackend backend;
    
    @BeforeEach
    public void setUp() throws IOException {
        tempDir = Files.createTempDirectory("backend-test");
        backend = new FilesystemBackend(tempDir, true, 10);
    }
    
    @AfterEach
    public void tearDown() throws IOException {
        deleteDirectory(tempDir);
    }
    
    private void deleteDirectory(Path dir) throws IOException {
        if (Files.exists(dir)) {
            Files.walk(dir)
                    .sorted((a, b) -> -a.compareTo(b))
                    .forEach(path -> {
                        try {
                            Files.delete(path);
                        } catch (IOException e) {
                            // Ignore
                        }
                    });
        }
    }
    
    @Test
    public void testWriteAndRead() {
        WriteResult writeResult = backend.write("/test.txt", "Hello Filesystem");
        assertTrue(writeResult.isSuccess());
        assertEquals("/test.txt", writeResult.getPath());
        
        String content = backend.read("/test.txt");
        assertTrue(content.contains("Hello Filesystem"));
        assertTrue(Files.exists(tempDir.resolve("test.txt")));
    }
    
    @Test
    public void testWriteExistingFile() {
        backend.write("/test.txt", "First");
        WriteResult result = backend.write("/test.txt", "Second");
        assertFalse(result.isSuccess());
        assertTrue(result.getError().contains("already exists"));
    }
    
    @Test
    public void testReadNonExistentFile() {
        String content = backend.read("/nonexistent.txt");
        assertTrue(content.contains("Error"));
        assertTrue(content.contains("not found"));
    }
    
    @Test
    public void testEditFile() {
        backend.write("/test.txt", "Hello Filesystem");
        EditResult result = backend.edit("/test.txt", "Filesystem", "Java");
        assertTrue(result.isSuccess());
        assertEquals(1, result.getOccurrences());
        
        String content = backend.read("/test.txt");
        assertTrue(content.contains("Hello Java"));
    }
    
    @Test
    public void testLsInfo() throws IOException {
        backend.write("/file1.txt", "content1");
        backend.write("/file2.txt", "content2");
        Files.createDirectories(tempDir.resolve("subdir"));
        
        List<FileInfo> infos = backend.lsInfo("/");
        assertTrue(infos.size() >= 2);
        
        boolean hasFile1 = false;
        boolean hasFile2 = false;
        
        for (FileInfo info : infos) {
            if (info.getPath().equals("/file1.txt")) hasFile1 = true;
            if (info.getPath().equals("/file2.txt")) hasFile2 = true;
        }
        
        assertTrue(hasFile1);
        assertTrue(hasFile2);
    }
    
    @Test
    public void testGrepRaw() {
        backend.write("/file1.txt", "Hello World\nGoodbye World");
        backend.write("/file2.txt", "Java Programming");
        
        Object result = backend.grepRaw("World", "/", null);
        assertTrue(result instanceof List);
        
        @SuppressWarnings("unchecked")
        List<GrepMatch> matches = (List<GrepMatch>) result;
        assertTrue(matches.size() >= 2);
    }
    
    @Test
    public void testGlobInfo() {
        backend.write("/test.txt", "content");
        backend.write("/test.md", "content");
        
        List<FileInfo> infos = backend.globInfo("*.txt", "/");
        assertTrue(infos.size() >= 1);
        
        boolean found = false;
        for (FileInfo info : infos) {
            if (info.getPath().equals("/test.txt")) {
                found = true;
            }
        }
        assertTrue(found);
    }
    
    @Test
    public void testNestedDirectories() throws IOException {
        Files.createDirectories(tempDir.resolve("dir1/dir2"));
        backend.write("/dir1/dir2/file.txt", "nested content");
        
        String content = backend.read("/dir1/dir2/file.txt");
        assertTrue(content.contains("nested content"));
    }
    
    @Test
    public void testPathTraversalPrevention() {
        WriteResult result = backend.write("/../etc/passwd", "malicious");
        assertFalse(result.isSuccess());
        assertTrue(result.getError() != null && 
                   (result.getError().contains("Path traversal") || 
                    result.getError().contains("outside root")));
    }
    
    @Test
    public void testLsNestedDirectories() throws IOException {
        Files.createDirectories(tempDir.resolve("src/utils"));
        Files.createDirectories(tempDir.resolve("docs/api"));
        
        backend.write("/config.json", "config");
        backend.write("/src/main.py", "code");
        backend.write("/src/utils/helper.py", "utils code");
        backend.write("/src/utils/common.py", "common utils");
        backend.write("/docs/readme.md", "documentation");
        backend.write("/docs/api/reference.md", "api docs");
        
        // Test root listing
        List<FileInfo> rootListing = backend.lsInfo("/");
        List<String> rootPaths = rootListing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toList());
        assertTrue(rootPaths.contains("/config.json"));
        assertTrue(rootPaths.contains("/src/"));
        assertTrue(rootPaths.contains("/docs/"));
        assertFalse(rootPaths.contains("/src/main.py"));
        assertFalse(rootPaths.contains("/src/utils/helper.py"));
        
        // Test src listing
        List<FileInfo> srcListing = backend.lsInfo("/src/");
        List<String> srcPaths = srcListing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toList());
        assertTrue(srcPaths.contains("/src/main.py"));
        assertTrue(srcPaths.contains("/src/utils/"));
        assertFalse(srcPaths.contains("/src/utils/helper.py"));
        
        // Test utils listing
        List<FileInfo> utilsListing = backend.lsInfo("/src/utils/");
        List<String> utilsPaths = utilsListing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toList());
        assertTrue(utilsPaths.contains("/src/utils/helper.py"));
        assertTrue(utilsPaths.contains("/src/utils/common.py"));
        assertEquals(2, utilsPaths.size());
        
        // Test empty listing
        List<FileInfo> emptyListing = backend.lsInfo("/nonexistent/");
        assertTrue(emptyListing.isEmpty());
    }
    
    @Test
    public void testLsTrailingSlash() {
        backend.write("/file.txt", "content");
        backend.write("/dir/nested.txt", "nested");
        
        List<FileInfo> listingWithSlash = backend.lsInfo("/");
        assertTrue(listingWithSlash.size() > 0);
        
        List<String> paths = listingWithSlash.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toList());
        assertEquals(paths, paths.stream().sorted().collect(java.util.stream.Collectors.toList()));
        
        // Test both with and without trailing slash
        List<FileInfo> listing1 = backend.lsInfo("/dir/");
        List<FileInfo> listing2 = backend.lsInfo("/dir");
        assertEquals(listing1.size(), listing2.size());
        
        List<String> paths1 = listing1.stream().map(FileInfo::getPath).collect(java.util.stream.Collectors.toList());
        List<String> paths2 = listing2.stream().map(FileInfo::getPath).collect(java.util.stream.Collectors.toList());
        assertEquals(paths1, paths2);
        
        // Test empty path
        List<FileInfo> emptyListing = backend.lsInfo("/nonexistent/");
        assertTrue(emptyListing.isEmpty());
    }
    
    @Test
    public void testGrepInvalidRegex() {
        backend.write("/file.txt", "test content");
        
        Object result = backend.grepRaw("[", "/", null);
        assertTrue(result instanceof String);
        assertTrue(((String) result).contains("Invalid regex"));
    }
    
    @Test
    public void testRecursiveGlob() {
        backend.write("/test.txt", "content");
        backend.write("/dir/test.md", "content");
        backend.write("/dir/subdir/test.txt", "content");
        
        List<FileInfo> infos = backend.globInfo("**/*.txt", "/");
        assertTrue(infos.size() >= 2);
        
        Set<String> paths = infos.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toSet());
        assertTrue(paths.contains("/test.txt"));
        assertTrue(paths.contains("/dir/subdir/test.txt"));
    }
}
