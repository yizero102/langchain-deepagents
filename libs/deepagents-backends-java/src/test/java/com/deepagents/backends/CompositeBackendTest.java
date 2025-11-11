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
}
