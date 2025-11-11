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
}
