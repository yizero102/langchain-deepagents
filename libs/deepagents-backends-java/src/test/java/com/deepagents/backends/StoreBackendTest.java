package com.deepagents.backends;

import com.deepagents.backends.impl.StoreBackend;
import com.deepagents.backends.protocol.EditResult;
import com.deepagents.backends.protocol.FileInfo;
import com.deepagents.backends.protocol.GrepMatch;
import com.deepagents.backends.protocol.WriteResult;
import com.deepagents.backends.store.InMemoryStore;
import com.deepagents.backends.store.Store;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class StoreBackendTest {
    
    private StoreBackend createBackend() {
        Store store = new InMemoryStore();
        return new StoreBackend(store);
    }
    
    @Test
    public void testStoreBackendCrudAndSearch() {
        StoreBackend be = createBackend();
        
        WriteResult writeResult = be.write("/docs/readme.md", "hello store");
        assertNotNull(writeResult);
        assertNull(writeResult.getError());
        assertEquals("/docs/readme.md", writeResult.getPath());
        
        String readResult = be.read("/docs/readme.md");
        assertTrue(readResult.contains("hello store"));
        
        EditResult editResult = be.edit("/docs/readme.md", "hello", "hi", false);
        assertNotNull(editResult);
        assertNull(editResult.getError());
        assertEquals(1, editResult.getOccurrences());
        
        List<FileInfo> infos = be.lsInfo("/docs/");
        boolean found = infos.stream().anyMatch(i -> i.getPath().equals("/docs/readme.md"));
        assertTrue(found);
        
        Object grepResult = be.grepRaw("hi", "/", null);
        assertTrue(grepResult instanceof List);
        @SuppressWarnings("unchecked")
        List<GrepMatch> matches = (List<GrepMatch>) grepResult;
        boolean grepFound = matches.stream().anyMatch(m -> m.getPath().equals("/docs/readme.md"));
        assertTrue(grepFound);
        
        List<FileInfo> globResult1 = be.globInfo("*.md", "/");
        assertEquals(0, globResult1.size());
        
        List<FileInfo> globResult2 = be.globInfo("**/*.md", "/");
        boolean globFound = globResult2.stream().anyMatch(i -> i.getPath().equals("/docs/readme.md"));
        assertTrue(globFound);
    }
    
    @Test
    public void testStoreBackendLsNestedDirectories() {
        StoreBackend be = createBackend();
        
        String[][] files = {
            {"/src/main.py", "main code"},
            {"/src/utils/helper.py", "helper code"},
            {"/src/utils/common.py", "common code"},
            {"/docs/readme.md", "readme"},
            {"/docs/api/reference.md", "api reference"},
            {"/config.json", "config"}
        };
        
        for (String[] file : files) {
            WriteResult res = be.write(file[0], file[1]);
            assertNull(res.getError());
        }
        
        List<FileInfo> rootListing = be.lsInfo("/");
        List<String> rootPaths = rootListing.stream().map(FileInfo::getPath).toList();
        assertTrue(rootPaths.contains("/config.json"));
        assertTrue(rootPaths.contains("/src/"));
        assertTrue(rootPaths.contains("/docs/"));
        assertFalse(rootPaths.contains("/src/main.py"));
        assertFalse(rootPaths.contains("/src/utils/helper.py"));
        assertFalse(rootPaths.contains("/docs/readme.md"));
        assertFalse(rootPaths.contains("/docs/api/reference.md"));
        
        List<FileInfo> srcListing = be.lsInfo("/src/");
        List<String> srcPaths = srcListing.stream().map(FileInfo::getPath).toList();
        assertTrue(srcPaths.contains("/src/main.py"));
        assertTrue(srcPaths.contains("/src/utils/"));
        assertFalse(srcPaths.contains("/src/utils/helper.py"));
        
        List<FileInfo> utilsListing = be.lsInfo("/src/utils/");
        List<String> utilsPaths = utilsListing.stream().map(FileInfo::getPath).toList();
        assertTrue(utilsPaths.contains("/src/utils/helper.py"));
        assertTrue(utilsPaths.contains("/src/utils/common.py"));
        assertEquals(2, utilsPaths.size());
        
        List<FileInfo> emptyListing = be.lsInfo("/nonexistent/");
        assertEquals(0, emptyListing.size());
    }
    
    @Test
    public void testStoreBackendLsTrailingSlash() {
        StoreBackend be = createBackend();
        
        String[][] files = {
            {"/file.txt", "content"},
            {"/dir/nested.txt", "nested"}
        };
        
        for (String[] file : files) {
            WriteResult res = be.write(file[0], file[1]);
            assertNull(res.getError());
        }
        
        List<FileInfo> listingFromRoot = be.lsInfo("/");
        assertTrue(listingFromRoot.size() > 0);
        
        List<FileInfo> listing1 = be.lsInfo("/dir/");
        List<FileInfo> listing2 = be.lsInfo("/dir");
        assertEquals(listing1.size(), listing2.size());
        
        List<String> paths1 = listing1.stream().map(FileInfo::getPath).toList();
        List<String> paths2 = listing2.stream().map(FileInfo::getPath).toList();
        assertEquals(paths1, paths2);
    }
    
    @Test
    public void testStoreBackendWriteExisting() {
        StoreBackend be = createBackend();
        
        WriteResult writeResult1 = be.write("/test.txt", "content");
        assertNull(writeResult1.getError());
        
        WriteResult writeResult2 = be.write("/test.txt", "new content");
        assertNotNull(writeResult2.getError());
        assertTrue(writeResult2.getError().contains("already exists"));
    }
    
    @Test
    public void testStoreBackendReadNonexistent() {
        StoreBackend be = createBackend();
        
        String readResult = be.read("/nonexistent.txt");
        assertTrue(readResult.contains("not found"));
    }
    
    @Test
    public void testStoreBackendEditNonexistent() {
        StoreBackend be = createBackend();
        
        EditResult editResult = be.edit("/nonexistent.txt", "old", "new", false);
        assertNotNull(editResult.getError());
        assertTrue(editResult.getError().contains("not found"));
    }
}
