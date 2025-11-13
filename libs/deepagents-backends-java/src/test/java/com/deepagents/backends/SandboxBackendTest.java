package com.deepagents.backends;

import com.deepagents.backends.impl.SandboxBackend;
import com.deepagents.backends.protocol.*;
import org.junit.jupiter.api.*;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class SandboxBackendTest {
    
    private static Process serverProcess;
    private static Path tempDir;
    private static SandboxBackend backend;
    private static final String BASE_URL = "http://localhost:8765";
    private static final int MAX_RETRIES = 20;
    private static final int RETRY_DELAY_MS = 500;
    
    @BeforeAll
    public static void setUpClass() throws Exception {
        tempDir = Files.createTempDirectory("sandbox_test_");
        System.out.println("Test directory: " + tempDir);
        
        String projectRoot = new File(System.getProperty("user.dir")).getParentFile().getParentFile().getAbsolutePath();
        String pythonExec = projectRoot + "/.venv/bin/python";
        
        File pythonFile = new File(pythonExec);
        if (!pythonFile.exists()) {
            pythonExec = System.getenv("PYTHON") != null ? System.getenv("PYTHON") : "python3";
        }
        
        ProcessBuilder pb = new ProcessBuilder(
            pythonExec, "-m", "fileserver.server", tempDir.toString(), "8765"
        );
        pb.directory(new File(projectRoot, "libs/deepagents-fileserver"));
        pb.redirectErrorStream(true);
        
        serverProcess = pb.start();
        
        new Thread(() -> {
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(serverProcess.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    System.out.println("[FileServer] " + line);
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }).start();
        
        System.out.println("Waiting for server to start...");
        if (!waitForServer(BASE_URL + "/health", MAX_RETRIES, RETRY_DELAY_MS)) {
            throw new RuntimeException("Server did not start within expected time");
        }
        System.out.println("Server is ready!");
        
        backend = new SandboxBackend(BASE_URL);
    }
    
    @AfterAll
    public static void tearDownClass() throws Exception {
        if (serverProcess != null) {
            serverProcess.destroy();
            serverProcess.waitFor();
            System.out.println("Server stopped");
        }
        
        if (tempDir != null && Files.exists(tempDir)) {
            Files.walk(tempDir)
                .sorted(Comparator.reverseOrder())
                .map(Path::toFile)
                .forEach(File::delete);
            System.out.println("Cleaned up: " + tempDir);
        }
    }
    
    private static boolean waitForServer(String healthUrl, int maxRetries, int delayMs) {
        for (int i = 0; i < maxRetries; i++) {
            try {
                URL url = new URL(healthUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(1000);
                conn.setReadTimeout(1000);
                
                int responseCode = conn.getResponseCode();
                if (responseCode == 200) {
                    return true;
                }
            } catch (Exception e) {
                // Server not ready yet
            }
            
            try {
                Thread.sleep(delayMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        return false;
    }
    
    @Test
    @Order(1)
    public void testWriteAndRead() {
        WriteResult writeResult = backend.write("test.txt", "Hello World");
        assertTrue(writeResult.isSuccess(), "Write should succeed");
        assertEquals("test.txt", writeResult.getPath());
        
        String content = backend.read("test.txt");
        assertTrue(content.contains("Hello World"), "Content should contain 'Hello World'");
    }
    
    @Test
    @Order(2)
    public void testWriteExistingFile() {
        backend.write("existing.txt", "First");
        WriteResult result = backend.write("existing.txt", "Second");
        assertFalse(result.isSuccess(), "Write to existing file should fail");
        assertTrue(result.getError().contains("already exists"), 
            "Error should mention 'already exists'");
    }
    
    @Test
    @Order(3)
    public void testReadNonExistentFile() {
        String content = backend.read("nonexistent.txt");
        assertTrue(content.contains("Error"), "Should return error message");
    }
    
    @Test
    @Order(4)
    public void testEditFile() {
        backend.write("edit_test.txt", "Hello World");
        EditResult result = backend.edit("edit_test.txt", "World", "Java");
        assertTrue(result.isSuccess(), "Edit should succeed");
        assertEquals(1, result.getOccurrences(), "Should replace 1 occurrence");
        
        String content = backend.read("edit_test.txt");
        assertTrue(content.contains("Hello Java"), "Content should contain 'Hello Java'");
    }
    
    @Test
    @Order(5)
    public void testEditWithMultipleOccurrences() {
        backend.write("multi_edit.txt", "foo bar foo");
        EditResult result = backend.edit("multi_edit.txt", "foo", "baz", false);
        assertTrue(result.isSuccess(), "Edit should succeed by replacing first occurrence");
        assertEquals(1, result.getOccurrences(), "Should replace only first occurrence");
        
        String content = backend.read("multi_edit.txt");
        assertTrue(content.contains("baz bar foo"), "Should contain 'baz bar foo' (first occurrence replaced)");
    }
    
    @Test
    @Order(6)
    public void testEditWithReplaceAll() {
        backend.write("replace_all.txt", "foo bar foo");
        EditResult result = backend.edit("replace_all.txt", "foo", "baz", true);
        assertTrue(result.isSuccess(), "Edit with replaceAll should succeed");
        assertEquals(2, result.getOccurrences(), "Should replace 2 occurrences");
        
        String content = backend.read("replace_all.txt");
        assertTrue(content.contains("baz bar baz"), "Content should contain 'baz bar baz'");
    }
    
    @Test
    @Order(7)
    public void testLsInfo() {
        backend.write("ls_file1.txt", "content1");
        backend.write("ls_file2.txt", "content2");
        backend.write("ls_dir/file3.txt", "content3");
        
        List<FileInfo> infos = backend.lsInfo(".");
        assertFalse(infos.isEmpty(), "Should return files");
        
        boolean hasFile1 = false;
        boolean hasFile2 = false;
        boolean hasDir = false;
        
        for (FileInfo info : infos) {
            if (info.getPath().contains("ls_file1.txt")) hasFile1 = true;
            if (info.getPath().contains("ls_file2.txt")) hasFile2 = true;
            if (info.getPath().contains("ls_dir") && info.isDir()) hasDir = true;
        }
        
        assertTrue(hasFile1, "Should list ls_file1.txt");
        assertTrue(hasFile2, "Should list ls_file2.txt");
        assertTrue(hasDir, "Should list ls_dir as directory");
    }
    
    @Test
    @Order(8)
    public void testLsInfoNestedDirectory() {
        backend.write("nested/sub/file.txt", "nested content");
        
        List<FileInfo> infos = backend.lsInfo("nested");
        assertEquals(1, infos.size(), "Should list one item");
        assertTrue(infos.get(0).isDir(), "Should be a directory");
        assertTrue(infos.get(0).getPath().contains("sub"), 
            "Should be the sub directory");
    }
    
    @Test
    @Order(9)
    public void testGrepRaw() {
        backend.write("grep_test1.txt", "This is a test file");
        backend.write("grep_test2.txt", "Another test here");
        
        Object result = backend.grepRaw("test", ".", null);
        assertTrue(result instanceof List, "Should return a list of matches");
        
        @SuppressWarnings("unchecked")
        List<GrepMatch> matches = (List<GrepMatch>) result;
        assertFalse(matches.isEmpty(), "Should find matches");
        
        boolean foundTest1 = false;
        boolean foundTest2 = false;
        
        for (GrepMatch match : matches) {
            if (match.getPath().contains("grep_test1.txt")) foundTest1 = true;
            if (match.getPath().contains("grep_test2.txt")) foundTest2 = true;
        }
        
        assertTrue(foundTest1, "Should find match in grep_test1.txt");
        assertTrue(foundTest2, "Should find match in grep_test2.txt");
    }
    
    @Test
    @Order(10)
    public void testGrepWithGlob() {
        backend.write("grep_glob.txt", "search me");
        backend.write("grep_glob.md", "search me too");
        
        Object result = backend.grepRaw("search", ".", "*.txt");
        assertTrue(result instanceof List, "Should return a list of matches");
        
        @SuppressWarnings("unchecked")
        List<GrepMatch> matches = (List<GrepMatch>) result;
        
        for (GrepMatch match : matches) {
            assertTrue(match.getPath().endsWith(".txt"), 
                "All matches should be from .txt files");
        }
    }
    
    @Test
    @Order(11)
    public void testGlobInfo() {
        backend.write("glob1.txt", "content1");
        backend.write("glob2.txt", "content2");
        backend.write("glob3.md", "content3");
        
        List<FileInfo> infos = backend.globInfo("*.txt", ".");
        assertFalse(infos.isEmpty(), "Should find .txt files");
        
        for (FileInfo info : infos) {
            assertTrue(info.getPath().endsWith(".txt"), "All results should be .txt files");
        }
    }
    
    @Test
    @Order(12)
    public void testGlobRecursive() {
        backend.write("rec/sub1/file1.txt", "content1");
        backend.write("rec/sub2/file2.txt", "content2");
        
        List<FileInfo> infos = backend.globInfo("**/*.txt", "rec");
        assertFalse(infos.isEmpty(), "Should find files recursively");
        
        boolean foundFile1 = false;
        boolean foundFile2 = false;
        
        for (FileInfo info : infos) {
            if (info.getPath().contains("file1.txt")) foundFile1 = true;
            if (info.getPath().contains("file2.txt")) foundFile2 = true;
        }
        
        assertTrue(foundFile1, "Should find file1.txt");
        assertTrue(foundFile2, "Should find file2.txt");
    }
    
    @Test
    @Order(13)
    public void testReadWithOffsetAndLimit() {
        StringBuilder content = new StringBuilder();
        for (int i = 1; i <= 100; i++) {
            content.append("Line ").append(i).append("\n");
        }
        backend.write("offset_test.txt", content.toString());
        
        String result = backend.read("offset_test.txt", 10, 5);
        assertTrue(result.contains("11 |"), "Should start from line 11 (offset 10)");
        
        String[] lines = result.split("\n");
        int contentLines = 0;
        for (String line : lines) {
            if (line.matches("\\s*\\d+\\s*\\|.*")) {
                contentLines++;
            }
        }
        assertTrue(contentLines <= 5, "Should contain at most 5 lines of content");
    }
    
    @Test
    @Order(14)
    public void testEditNonExistentFile() {
        EditResult result = backend.edit("not_exists.txt", "old", "new");
        assertFalse(result.isSuccess(), "Edit non-existent file should fail");
        assertTrue(result.getError().contains("not found") || result.getError().contains("Error"), 
            "Error should mention file not found");
    }
    
    @Test
    @Order(15)
    public void testUnicodeContent() {
        String unicodeContent = "Hello 世界 🌍 Привет";
        backend.write("unicode.txt", unicodeContent);
        
        String content = backend.read("unicode.txt");
        assertTrue(content.contains("世界"), "Should handle Chinese characters");
        assertTrue(content.contains("🌍"), "Should handle emojis");
        assertTrue(content.contains("Привет"), "Should handle Cyrillic characters");
    }
    
    @Test
    @Order(16)
    public void testEmptyFileWrite() {
        WriteResult result = backend.write("empty.txt", "");
        assertTrue(result.isSuccess(), "Should write empty file");
        
        String content = backend.read("empty.txt");
        assertNotNull(content, "Should read empty file");
    }
    
    @Test
    @Order(17)
    public void testLargeContent() {
        StringBuilder largeContent = new StringBuilder();
        for (int i = 0; i < 1000; i++) {
            largeContent.append("This is line ").append(i).append(" with some content.\n");
        }
        
        WriteResult writeResult = backend.write("large.txt", largeContent.toString());
        assertTrue(writeResult.isSuccess(), "Should write large file");
        
        String content = backend.read("large.txt");
        assertNotNull(content, "Should read large file");
        assertTrue(content.length() > 0, "Content should not be empty");
    }
    
    @Test
    @Order(18)
    public void testMultilineEdit() {
        String multilineContent = "Line 1\nLine 2\nLine 3\nLine 4";
        backend.write("multiline.txt", multilineContent);
        
        EditResult result = backend.edit("multiline.txt", "Line 2\nLine 3", "New Lines");
        assertTrue(result.isSuccess(), "Should edit multiline content");
        
        String content = backend.read("multiline.txt");
        assertTrue(content.contains("New Lines"), "Should contain edited content");
    }
    
    @Test
    @Order(19)
    public void testSpecialCharactersInFilename() {
        String filename = "special-file_test.txt";
        WriteResult result = backend.write(filename, "special content");
        assertTrue(result.isSuccess(), "Should handle special characters in filename");
        
        String content = backend.read(filename);
        assertTrue(content.contains("special content"), "Should read file with special characters");
    }
    
    @Test
    @Order(20)
    public void testGrepNoMatches() {
        backend.write("no_match.txt", "nothing to see here");
        
        Object result = backend.grepRaw("nonexistent_pattern_xyz", ".", null);
        assertTrue(result instanceof List, "Should return a list");
        
        @SuppressWarnings("unchecked")
        List<GrepMatch> matches = (List<GrepMatch>) result;
        assertTrue(matches.isEmpty(), "Should return empty list when no matches");
    }
    
    @Test
    @Order(21)
    public void testGlobNoMatches() {
        List<FileInfo> infos = backend.globInfo("*.nonexistent", ".");
        assertTrue(infos.isEmpty(), "Should return empty list when no matches");
    }
    
    @Test
    @Order(22)
    public void testEditWithNoMatches() {
        backend.write("no_match_edit.txt", "original content");
        EditResult result = backend.edit("no_match_edit.txt", "nonexistent", "replacement");
        assertFalse(result.isSuccess(), "Edit with no matches should fail");
    }
    
    @Test
    @Order(23)
    public void testDeepNestedPaths() {
        String deepPath = "level1/level2/level3/level4/level5/deep_file.txt";
        WriteResult result = backend.write(deepPath, "deep content");
        assertTrue(result.isSuccess(), "Should handle deep nested paths");
        
        String content = backend.read(deepPath);
        assertTrue(content.contains("deep content"), "Should read from deep path");
    }
    
    @Test
    @Order(24)
    public void testBaseUrlConfiguration() {
        String baseUrl = backend.getBaseUrl();
        assertNotNull(baseUrl, "Base URL should not be null");
        assertEquals(BASE_URL, baseUrl, "Base URL should match configured value");
    }
    
    @Test
    @Order(25)
    public void testApiKeyConfiguration() {
        SandboxBackend backendWithKey = new SandboxBackend(BASE_URL, "test-api-key");
        assertNotNull(backendWithKey, "Should create backend with API key");
        assertEquals(BASE_URL, backendWithKey.getBaseUrl(), "Base URL should be set correctly");
    }
    
    @Test
    @Order(26)
    public void testErrorHandlingNetworkFailure() {
        SandboxBackend invalidBackend = new SandboxBackend("http://localhost:99999");
        String result = invalidBackend.read("test.txt");
        assertTrue(result.contains("Error"), "Should handle network errors gracefully");
    }
}
