package com.deepagents.backends;

import com.deepagents.backends.impl.CompositeBackend;
import com.deepagents.backends.impl.StateBackend;
import com.deepagents.backends.protocol.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

public class CompositeBackendTest {
    
    private CompositeBackend compositeBackend;
    private StateBackend defaultBackend;
    private StateBackend memoryBackend;
    
    @BeforeEach
    public void setUp() {
        defaultBackend = new StateBackend();
        memoryBackend = new StateBackend();
        
        Map<String, BackendProtocol> routes = new HashMap<>();
        routes.put("/memory/", memoryBackend);
        
        compositeBackend = new CompositeBackend(defaultBackend, routes);
    }
    
    @Test
    public void testWriteToDefaultBackend() {
        WriteResult result = compositeBackend.write("/test.txt", "default content");
        assertTrue(result.isSuccess());
        
        String content = compositeBackend.read("/test.txt");
        assertTrue(content.contains("default content"));
    }
    
    @Test
    public void testWriteToRoutedBackend() {
        WriteResult result = compositeBackend.write("/memory/test.txt", "memory content");
        assertTrue(result.isSuccess());
        
        String content = compositeBackend.read("/memory/test.txt");
        assertTrue(content.contains("memory content"));
    }
    
    @Test
    public void testLsInfoRoot() {
        compositeBackend.write("/default.txt", "content");
        compositeBackend.write("/memory/memory.txt", "content");
        
        List<FileInfo> infos = compositeBackend.lsInfo("/");
        
        boolean hasDefault = false;
        boolean hasMemoryDir = false;
        
        for (FileInfo info : infos) {
            if (info.getPath().equals("/default.txt")) hasDefault = true;
            if (info.getPath().equals("/memory/")) {
                hasMemoryDir = true;
                assertTrue(info.isDir());
            }
        }
        
        assertTrue(hasDefault);
        assertTrue(hasMemoryDir);
    }
    
    @Test
    public void testLsInfoRoutedPath() {
        compositeBackend.write("/memory/file1.txt", "content1");
        compositeBackend.write("/memory/file2.txt", "content2");
        
        List<FileInfo> infos = compositeBackend.lsInfo("/memory/");
        
        boolean hasFile1 = false;
        boolean hasFile2 = false;
        
        for (FileInfo info : infos) {
            if (info.getPath().equals("/memory/file1.txt")) hasFile1 = true;
            if (info.getPath().equals("/memory/file2.txt")) hasFile2 = true;
        }
        
        assertTrue(hasFile1);
        assertTrue(hasFile2);
    }
    
    @Test
    public void testEditRoutedFile() {
        compositeBackend.write("/memory/test.txt", "Hello World");
        EditResult result = compositeBackend.edit("/memory/test.txt", "World", "Composite");
        assertTrue(result.isSuccess());
        
        String content = compositeBackend.read("/memory/test.txt");
        assertTrue(content.contains("Hello Composite"));
    }
    
    @Test
    public void testGrepAcrossBackends() {
        compositeBackend.write("/default.txt", "Hello World");
        compositeBackend.write("/memory/memory.txt", "Hello Java");
        
        Object result = compositeBackend.grepRaw("Hello", "/", null);
        assertTrue(result instanceof List);
        
        @SuppressWarnings("unchecked")
        List<GrepMatch> matches = (List<GrepMatch>) result;
        assertTrue(matches.size() >= 2);
        
        boolean hasDefault = false;
        boolean hasMemory = false;
        
        for (GrepMatch match : matches) {
            if (match.getPath().equals("/default.txt")) hasDefault = true;
            if (match.getPath().equals("/memory/memory.txt")) hasMemory = true;
        }
        
        assertTrue(hasDefault);
        assertTrue(hasMemory);
    }
    
    @Test
    public void testGlobAcrossBackends() {
        compositeBackend.write("/test.txt", "default");
        compositeBackend.write("/memory/test.txt", "memory");
        
        List<FileInfo> infos = compositeBackend.globInfo("*.txt", "/");
        assertTrue(infos.size() >= 2);
        
        boolean hasDefault = false;
        boolean hasMemory = false;
        
        for (FileInfo info : infos) {
            if (info.getPath().equals("/test.txt")) hasDefault = true;
            if (info.getPath().equals("/memory/test.txt")) hasMemory = true;
        }
        
        assertTrue(hasDefault);
        assertTrue(hasMemory);
    }
    
    @Test
    public void testMultipleRoutes() {
        StateBackend archiveBackend = new StateBackend();
        StateBackend cacheBackend = new StateBackend();
        
        Map<String, BackendProtocol> routes = new HashMap<>();
        routes.put("/memory/", memoryBackend);
        routes.put("/archive/", archiveBackend);
        routes.put("/cache/", cacheBackend);
        
        CompositeBackend multiRouteBackend = new CompositeBackend(defaultBackend, routes);
        
        // Write to different backends
        multiRouteBackend.write("/temp.txt", "ephemeral data");
        multiRouteBackend.write("/memory/important.md", "long-term memory");
        multiRouteBackend.write("/archive/old.log", "archived log");
        multiRouteBackend.write("/cache/session.json", "cached session");
        
        // Test root listing includes all routes
        List<FileInfo> rootListing = multiRouteBackend.lsInfo("/");
        Set<String> paths = rootListing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toSet());
        
        assertTrue(paths.contains("/temp.txt"));
        assertTrue(paths.contains("/memory/"));
        assertTrue(paths.contains("/archive/"));
        assertTrue(paths.contains("/cache/"));
        
        // Test specific route listing
        List<FileInfo> memListing = multiRouteBackend.lsInfo("/memory/");
        Set<String> memPaths = memListing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toSet());
        assertTrue(memPaths.contains("/memory/important.md"));
        assertFalse(memPaths.contains("/temp.txt"));
        
        // Test grep across all backends
        Object allMatches = multiRouteBackend.grepRaw(".", "/", null);
        assertTrue(allMatches instanceof List);
        @SuppressWarnings("unchecked")
        List<GrepMatch> matches = (List<GrepMatch>) allMatches;
        Set<String> matchPaths = matches.stream()
                .map(GrepMatch::getPath)
                .collect(java.util.stream.Collectors.toSet());
        assertTrue(matchPaths.contains("/temp.txt"));
        assertTrue(matchPaths.contains("/memory/important.md"));
        assertTrue(matchPaths.contains("/archive/old.log"));
        assertTrue(matchPaths.contains("/cache/session.json"));
        
        // Test edit in routed backend
        EditResult editRes = multiRouteBackend.edit("/memory/important.md", "long-term", "persistent", false);
        assertTrue(editRes.isSuccess());
        assertEquals(1, editRes.getOccurrences());
        
        String updatedContent = multiRouteBackend.read("/memory/important.md");
        assertTrue(updatedContent.contains("persistent memory"));
    }
    
    @Test
    public void testLsNestedDirectories() {
        defaultBackend.write("/temp.txt", "temp");
        defaultBackend.write("/work/file1.txt", "work file 1");
        defaultBackend.write("/work/projects/proj1.txt", "project 1");
        
        memoryBackend.write("/important.txt", "important");
        memoryBackend.write("/diary/entry1.txt", "diary entry");
        
        // Root listing
        List<FileInfo> rootListing = compositeBackend.lsInfo("/");
        List<String> rootPaths = rootListing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toList());
        assertTrue(rootPaths.contains("/temp.txt"));
        assertTrue(rootPaths.contains("/work/"));
        assertTrue(rootPaths.contains("/memory/"));
        assertFalse(rootPaths.contains("/work/file1.txt"));
        assertFalse(rootPaths.contains("/memory/important.txt"));
        
        // Work listing
        List<FileInfo> workListing = compositeBackend.lsInfo("/work/");
        List<String> workPaths = workListing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toList());
        assertTrue(workPaths.contains("/work/file1.txt"));
        assertTrue(workPaths.contains("/work/projects/"));
        assertFalse(workPaths.contains("/work/projects/proj1.txt"));
        
        // Memory listing
        List<FileInfo> memListing = compositeBackend.lsInfo("/memory/");
        List<String> memPaths = memListing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toList());
        assertTrue(memPaths.contains("/memory/important.txt"));
        assertTrue(memPaths.contains("/memory/diary/"));
        assertFalse(memPaths.contains("/memory/diary/entry1.txt"));
    }
    
    @Test
    public void testLsTrailingSlash() {
        defaultBackend.write("/file.txt", "content");
        memoryBackend.write("/item.txt", "store content");
        
        List<FileInfo> listing = compositeBackend.lsInfo("/");
        List<String> paths = listing.stream()
                .map(FileInfo::getPath)
                .collect(java.util.stream.Collectors.toList());
        assertEquals(paths, paths.stream().sorted().collect(java.util.stream.Collectors.toList()));
        
        // Empty listing
        List<FileInfo> emptyListing = compositeBackend.lsInfo("/memory/nonexistent/");
        assertTrue(emptyListing.isEmpty());
        
        List<FileInfo> emptyListing2 = compositeBackend.lsInfo("/nonexistent/");
        assertTrue(emptyListing2.isEmpty());
        
        // Trailing slash handling
        List<FileInfo> listing1 = compositeBackend.lsInfo("/memory/");
        List<FileInfo> listing2 = compositeBackend.lsInfo("/memory");
        assertEquals(listing1.size(), listing2.size());
        
        List<String> paths1 = listing1.stream().map(FileInfo::getPath).collect(java.util.stream.Collectors.toList());
        List<String> paths2 = listing2.stream().map(FileInfo::getPath).collect(java.util.stream.Collectors.toList());
        assertEquals(paths1, paths2);
    }
}
