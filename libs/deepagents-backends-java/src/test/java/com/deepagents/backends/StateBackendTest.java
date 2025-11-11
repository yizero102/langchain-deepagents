package com.deepagents.backends;

import com.deepagents.backends.impl.StateBackend;
import com.deepagents.backends.protocol.*;
import com.deepagents.backends.utils.BackendUtils;
import com.deepagents.backends.utils.FileData;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.*;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

public class StateBackendTest {
    
    private StateBackend backend;
    
    @BeforeEach
    public void setUp() {
        backend = new StateBackend();
    }
    
    @Test
    public void testWriteAndRead() {
        WriteResult writeResult = backend.write("/test.txt", "Hello World");
        assertTrue(writeResult.isSuccess());
        assertEquals("/test.txt", writeResult.getPath());
        assertNotNull(writeResult.getFilesUpdate());
        
        String content = backend.read("/test.txt");
        assertTrue(content.contains("Hello World"));
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
        backend.write("/test.txt", "Hello World");
        EditResult result = backend.edit("/test.txt", "World", "Java");
        assertTrue(result.isSuccess());
        assertEquals(1, result.getOccurrences());
        
        String content = backend.read("/test.txt");
        assertTrue(content.contains("Hello Java"));
    }
    
    @Test
    public void testEditWithMultipleOccurrences() {
        backend.write("/test.txt", "foo bar foo");
        EditResult result = backend.edit("/test.txt", "foo", "baz", false);
        assertFalse(result.isSuccess());
        assertTrue(result.getError().contains("appears 2 times"));
    }
    
    @Test
    public void testEditWithReplaceAll() {
        backend.write("/test.txt", "foo bar foo");
        EditResult result = backend.edit("/test.txt", "foo", "baz", true);
        assertTrue(result.isSuccess());
        assertEquals(2, result.getOccurrences());
        
        String content = backend.read("/test.txt");
        assertTrue(content.contains("baz bar baz"));
    }
    
    @Test
    public void testLsInfo() {
        backend.write("/file1.txt", "content1");
        backend.write("/file2.txt", "content2");
        backend.write("/dir/file3.txt", "content3");
        
        List<FileInfo> infos = backend.lsInfo("/");
        assertEquals(3, infos.size());
        
        boolean hasFile1 = false;
        boolean hasFile2 = false;
        boolean hasDir = false;
        
        for (FileInfo info : infos) {
            if (info.getPath().equals("/file1.txt")) hasFile1 = true;
            if (info.getPath().equals("/file2.txt")) hasFile2 = true;
            if (info.getPath().equals("/dir/")) {
                hasDir = true;
                assertTrue(info.isDir());
            }
        }
        
        assertTrue(hasFile1);
        assertTrue(hasFile2);
        assertTrue(hasDir);
    }
    
    @Test
    public void testGrepRaw() {
        backend.write("/file1.txt", "Hello World\nGoodbye World");
        backend.write("/file2.txt", "Java Programming");
        
        Object result = backend.grepRaw("World", "/", null);
        assertTrue(result instanceof List);
        
        @SuppressWarnings("unchecked")
        List<GrepMatch> matches = (List<GrepMatch>) result;
        assertEquals(2, matches.size());
        
        for (GrepMatch match : matches) {
            assertTrue(match.getText().contains("World"));
        }
    }
    
    @Test
    public void testGlobInfo() {
        backend.write("/test.txt", "content");
        backend.write("/test.md", "content");
        backend.write("/dir/test.txt", "content");
        
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
    public void testReadWithOffsetAndLimit() {
        StringBuilder content = new StringBuilder();
        for (int i = 1; i <= 100; i++) {
            content.append("Line ").append(i).append("\n");
        }
        backend.write("/test.txt", content.toString());
        
        String result = backend.read("/test.txt", 10, 5);
        assertTrue(result.contains("Line 11"));
        assertTrue(result.contains("Line 15"));
        assertFalse(result.contains("Line 10"));
        assertFalse(result.contains("Line 16"));
    }
    
    @Test
    public void testEmptyContent() {
        backend.write("/empty.txt", "");
        String content = backend.read("/empty.txt");
        assertTrue(content.contains("empty contents"));
    }
    
    @Test
    public void testLsNestedDirectories() {
        Map<String, String> files = new LinkedHashMap<>();
        files.put("/src/main.py", "main code");
        files.put("/src/utils/helper.py", "helper code");
        files.put("/src/utils/common.py", "common code");
        files.put("/docs/readme.md", "readme");
        files.put("/docs/api/reference.md", "api reference");
        files.put("/config.json", "config");
        
        for (Map.Entry<String, String> entry : files.entrySet()) {
            backend.write(entry.getKey(), entry.getValue());
        }
        
        // Test root listing
        List<FileInfo> rootListing = backend.lsInfo("/");
        List<String> rootPaths = rootListing.stream()
                .map(FileInfo::getPath)
                .collect(Collectors.toList());
        assertTrue(rootPaths.contains("/config.json"));
        assertTrue(rootPaths.contains("/src/"));
        assertTrue(rootPaths.contains("/docs/"));
        assertFalse(rootPaths.contains("/src/main.py"));
        assertFalse(rootPaths.contains("/src/utils/helper.py"));
        
        // Test src listing
        List<FileInfo> srcListing = backend.lsInfo("/src/");
        List<String> srcPaths = srcListing.stream()
                .map(FileInfo::getPath)
                .collect(Collectors.toList());
        assertTrue(srcPaths.contains("/src/main.py"));
        assertTrue(srcPaths.contains("/src/utils/"));
        assertFalse(srcPaths.contains("/src/utils/helper.py"));
        
        // Test utils listing
        List<FileInfo> utilsListing = backend.lsInfo("/src/utils/");
        List<String> utilsPaths = utilsListing.stream()
                .map(FileInfo::getPath)
                .collect(Collectors.toList());
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
        assertEquals(2, listingWithSlash.size());
        
        List<String> paths = listingWithSlash.stream()
                .map(FileInfo::getPath)
                .collect(Collectors.toList());
        assertTrue(paths.contains("/file.txt"));
        assertTrue(paths.contains("/dir/"));
        
        List<FileInfo> listingFromDir = backend.lsInfo("/dir/");
        assertEquals(1, listingFromDir.size());
        assertEquals("/dir/nested.txt", listingFromDir.get(0).getPath());
    }
    
    @Test
    public void testGrepInvalidRegex() {
        backend.write("/file.txt", "test content");
        
        Object result = backend.grepRaw("[", "/", null);
        assertTrue(result instanceof String);
        assertTrue(((String) result).contains("Invalid regex"));
    }
    
    @Test
    public void testEditNonExistentFile() {
        EditResult result = backend.edit("/missing.txt", "old", "new");
        assertFalse(result.isSuccess());
        assertTrue(result.getError().contains("not found"));
    }
}
