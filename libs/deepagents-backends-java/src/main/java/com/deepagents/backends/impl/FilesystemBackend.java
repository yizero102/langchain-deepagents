package com.deepagents.backends.impl;

import com.deepagents.backends.protocol.*;
import com.deepagents.backends.utils.BackendUtils;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

public class FilesystemBackend implements BackendProtocol {
    
    private final Path rootDir;
    private final boolean virtualMode;
    private final long maxFileSizeBytes;
    
    public FilesystemBackend(Path rootDir, boolean virtualMode, int maxFileSizeMb) {
        this.rootDir = rootDir != null ? rootDir.toAbsolutePath() : Paths.get("").toAbsolutePath();
        this.virtualMode = virtualMode;
        this.maxFileSizeBytes = maxFileSizeMb * 1024L * 1024L;
    }
    
    public FilesystemBackend() {
        this(null, false, 10);
    }
    
    public FilesystemBackend(Path rootDir) {
        this(rootDir, false, 10);
    }
    
    private Path resolvePath(String key) {
        if (virtualMode) {
            String vpath = key.startsWith("/") ? key : "/" + key;
            if (vpath.contains("..") || vpath.startsWith("~")) {
                throw new IllegalArgumentException("Path traversal not allowed");
            }
            Path full = rootDir.resolve(vpath.substring(1)).normalize();
            if (!full.startsWith(rootDir)) {
                throw new IllegalArgumentException(String.format("Path:%s outside root directory: %s", full, rootDir));
            }
            return full;
        }
        
        Path path = Paths.get(key);
        if (path.isAbsolute()) {
            return path;
        }
        return rootDir.resolve(path).normalize();
    }

    @Override
    public List<FileInfo> lsInfo(String path) {
        Path dirPath;
        try {
            dirPath = resolvePath(path);
        } catch (IllegalArgumentException e) {
            return new ArrayList<>();
        }
        
        if (!Files.exists(dirPath) || !Files.isDirectory(dirPath)) {
            return new ArrayList<>();
        }
        
        List<FileInfo> results = new ArrayList<>();
        final String cwdStr = rootDir.toString().endsWith("/") 
                ? rootDir.toString() 
                : rootDir.toString() + "/";
        final String rootDirStr = rootDir.toString();
        
        try (Stream<Path> stream = Files.list(dirPath)) {
            stream.forEach(childPath -> {
                try {
                    boolean isFile = Files.isRegularFile(childPath);
                    boolean isDir = Files.isDirectory(childPath);
                    
                    String absPath = childPath.toString();
                    
                    if (!virtualMode) {
                        if (isFile) {
                            try {
                                BasicFileAttributes attrs = Files.readAttributes(childPath, BasicFileAttributes.class);
                                results.add(new FileInfo(
                                        absPath,
                                        false,
                                        (int) attrs.size(),
                                        formatInstant(attrs.lastModifiedTime().toInstant())
                                ));
                            } catch (IOException e) {
                                results.add(new FileInfo(absPath, false));
                            }
                        } else if (isDir) {
                            try {
                                BasicFileAttributes attrs = Files.readAttributes(childPath, BasicFileAttributes.class);
                                results.add(new FileInfo(
                                        absPath + "/",
                                        true,
                                        0,
                                        formatInstant(attrs.lastModifiedTime().toInstant())
                                ));
                            } catch (IOException e) {
                                results.add(new FileInfo(absPath + "/", true));
                            }
                        }
                    } else {
                        String relativePath;
                        if (absPath.startsWith(cwdStr)) {
                            relativePath = absPath.substring(cwdStr.length());
                        } else if (absPath.startsWith(rootDirStr)) {
                            relativePath = absPath.substring(rootDirStr.length());
                            if (relativePath.startsWith("/")) {
                                relativePath = relativePath.substring(1);
                            }
                        } else {
                            relativePath = absPath;
                        }
                        
                        String virtPath = "/" + relativePath;
                        
                        if (isFile) {
                            try {
                                BasicFileAttributes attrs = Files.readAttributes(childPath, BasicFileAttributes.class);
                                results.add(new FileInfo(
                                        virtPath,
                                        false,
                                        (int) attrs.size(),
                                        formatInstant(attrs.lastModifiedTime().toInstant())
                                ));
                            } catch (IOException e) {
                                results.add(new FileInfo(virtPath, false));
                            }
                        } else if (isDir) {
                            try {
                                BasicFileAttributes attrs = Files.readAttributes(childPath, BasicFileAttributes.class);
                                results.add(new FileInfo(
                                        virtPath + "/",
                                        true,
                                        0,
                                        formatInstant(attrs.lastModifiedTime().toInstant())
                                ));
                            } catch (IOException e) {
                                results.add(new FileInfo(virtPath + "/", true));
                            }
                        }
                    }
                } catch (Exception e) {
                    // Skip files that cause errors
                }
            });
        } catch (IOException e) {
            // Return empty list on error
        }
        
        results.sort(Comparator.comparing(FileInfo::getPath));
        return results;
    }
    
    private String formatInstant(Instant instant) {
        return instant.atOffset(ZoneOffset.UTC).format(DateTimeFormatter.ISO_INSTANT);
    }

    @Override
    public String read(String filePath, int offset, int limit) {
        Path resolvedPath;
        try {
            resolvedPath = resolvePath(filePath);
        } catch (IllegalArgumentException e) {
            return String.format("Error: File '%s' not found", filePath);
        }
        
        if (!Files.exists(resolvedPath) || !Files.isRegularFile(resolvedPath)) {
            return String.format("Error: File '%s' not found", filePath);
        }
        
        try {
            String content = Files.readString(resolvedPath);
            
            String emptyMsg = BackendUtils.checkEmptyContent(content);
            if (emptyMsg != null) {
                return emptyMsg;
            }
            
            String[] lines = content.split("\n", -1);
            int startIdx = offset;
            int endIdx = Math.min(startIdx + limit, lines.length);
            
            if (startIdx >= lines.length) {
                return String.format("Error: Line offset %d exceeds file length (%d lines)", offset, lines.length);
            }
            
            List<String> selectedLines = Arrays.asList(Arrays.copyOfRange(lines, startIdx, endIdx));
            return BackendUtils.formatContentWithLineNumbers(selectedLines, startIdx + 1);
        } catch (IOException e) {
            return String.format("Error reading file '%s': %s", filePath, e.getMessage());
        }
    }

    @Override
    public WriteResult write(String filePath, String content) {
        Path resolvedPath;
        try {
            resolvedPath = resolvePath(filePath);
        } catch (IllegalArgumentException e) {
            return WriteResult.error(String.format("Error writing file '%s': %s", filePath, e.getMessage()));
        }
        
        if (Files.exists(resolvedPath)) {
            return WriteResult.error(String.format("Cannot write to %s because it already exists. Read and then make an edit, or write to a new path.", filePath));
        }
        
        try {
            Files.createDirectories(resolvedPath.getParent());
            Files.writeString(resolvedPath, content);
            return WriteResult.success(filePath);
        } catch (IOException e) {
            return WriteResult.error(String.format("Error writing file '%s': %s", filePath, e.getMessage()));
        }
    }

    @Override
    public EditResult edit(String filePath, String oldString, String newString, boolean replaceAll) {
        Path resolvedPath;
        try {
            resolvedPath = resolvePath(filePath);
        } catch (IllegalArgumentException e) {
            return EditResult.error(String.format("Error: File '%s' not found", filePath));
        }
        
        if (!Files.exists(resolvedPath) || !Files.isRegularFile(resolvedPath)) {
            return EditResult.error(String.format("Error: File '%s' not found", filePath));
        }
        
        try {
            String content = Files.readString(resolvedPath);
            Object result = BackendUtils.performStringReplacement(content, oldString, newString, replaceAll);
            
            if (result instanceof String) {
                return EditResult.error((String) result);
            }
            
            BackendUtils.ReplacementResult replacement = (BackendUtils.ReplacementResult) result;
            Files.writeString(resolvedPath, replacement.getNewContent());
            
            return EditResult.success(filePath, replacement.getOccurrences());
        } catch (IOException e) {
            return EditResult.error(String.format("Error editing file '%s': %s", filePath, e.getMessage()));
        }
    }

    @Override
    public Object grepRaw(String pattern, String path, String glob) {
        Pattern regex;
        try {
            regex = Pattern.compile(pattern);
        } catch (Exception e) {
            return "Invalid regex pattern: " + e.getMessage();
        }
        
        Path baseFull;
        try {
            baseFull = resolvePath(path != null ? path : ".");
        } catch (IllegalArgumentException e) {
            return new ArrayList<GrepMatch>();
        }
        
        if (!Files.exists(baseFull)) {
            return new ArrayList<GrepMatch>();
        }
        
        Map<String, List<Map.Entry<Integer, String>>> results = pythonSearch(regex, baseFull, glob);
        
        List<GrepMatch> matches = new ArrayList<>();
        for (Map.Entry<String, List<Map.Entry<Integer, String>>> entry : results.entrySet()) {
            for (Map.Entry<Integer, String> item : entry.getValue()) {
                matches.add(new GrepMatch(entry.getKey(), item.getKey(), item.getValue()));
            }
        }
        return matches;
    }
    
    private Map<String, List<Map.Entry<Integer, String>>> pythonSearch(Pattern regex, Path baseFull, String includeGlob) {
        Map<String, List<Map.Entry<Integer, String>>> results = new HashMap<>();
        Path root = Files.isDirectory(baseFull) ? baseFull : baseFull.getParent();
        
        try {
            Files.walkFileTree(root, new SimpleFileVisitor<Path>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                    try {
                        if (!Files.isRegularFile(file)) {
                            return FileVisitResult.CONTINUE;
                        }
                        
                        if (includeGlob != null && !matchesGlob(file.getFileName().toString(), includeGlob)) {
                            return FileVisitResult.CONTINUE;
                        }
                        
                        if (attrs.size() > maxFileSizeBytes) {
                            return FileVisitResult.CONTINUE;
                        }
                        
                        String content = Files.readString(file);
                        String[] lines = content.split("\n", -1);
                        
                        for (int lineNum = 0; lineNum < lines.length; lineNum++) {
                            String line = lines[lineNum];
                            Matcher matcher = regex.matcher(line);
                            if (matcher.find()) {
                                String virtPath;
                                if (virtualMode) {
                                    try {
                                        virtPath = "/" + rootDir.relativize(file.toRealPath()).toString();
                                    } catch (Exception e) {
                                        return FileVisitResult.CONTINUE;
                                    }
                                } else {
                                    virtPath = file.toString();
                                }
                                results.computeIfAbsent(virtPath, k -> new ArrayList<>())
                                        .add(Map.entry(lineNum + 1, line));
                            }
                        }
                    } catch (IOException e) {
                        // Skip files that can't be read
                    }
                    return FileVisitResult.CONTINUE;
                }
            });
        } catch (IOException e) {
            // Return empty results on error
        }
        
        return results;
    }
    
    private boolean matchesGlob(String filename, String glob) {
        String regexPattern = glob
                .replace(".", "\\.")
                .replace("*", ".*")
                .replace("?", ".");
        return filename.matches(regexPattern);
    }

    @Override
    public List<FileInfo> globInfo(String pattern, String path) {
        String searchPath = path.equals("/") ? "" : path;
        Path resolvedPath;
        try {
            resolvedPath = resolvePath(searchPath.isEmpty() ? "." : searchPath);
        } catch (IllegalArgumentException e) {
            return new ArrayList<>();
        }
        
        if (!Files.exists(resolvedPath) || !Files.isDirectory(resolvedPath)) {
            return new ArrayList<>();
        }
        
        List<FileInfo> results = new ArrayList<>();
        String cleanPattern = pattern.startsWith("/") ? pattern.substring(1) : pattern;
        
        try {
            PathMatcher matcher = FileSystems.getDefault().getPathMatcher("glob:" + cleanPattern);
            
            Files.walkFileTree(resolvedPath, new SimpleFileVisitor<Path>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                    try {
                        if (!Files.isRegularFile(file)) {
                            return FileVisitResult.CONTINUE;
                        }
                        
                        Path relative = resolvedPath.relativize(file);
                        if (matcher.matches(relative)) {
                            String absPath = file.toString();
                            if (!virtualMode) {
                                results.add(new FileInfo(
                                        absPath,
                                        false,
                                        (int) attrs.size(),
                                        formatInstant(attrs.lastModifiedTime().toInstant())
                                ));
                            } else {
                                String cwdStr = rootDir.toString();
                                if (!cwdStr.endsWith("/")) {
                                    cwdStr += "/";
                                }
                                String relativePath;
                                if (absPath.startsWith(cwdStr)) {
                                    relativePath = absPath.substring(cwdStr.length());
                                } else if (absPath.startsWith(rootDir.toString())) {
                                    relativePath = absPath.substring(rootDir.toString().length());
                                    if (relativePath.startsWith("/")) {
                                        relativePath = relativePath.substring(1);
                                    }
                                } else {
                                    relativePath = absPath;
                                }
                                String virt = "/" + relativePath;
                                results.add(new FileInfo(
                                        virt,
                                        false,
                                        (int) attrs.size(),
                                        formatInstant(attrs.lastModifiedTime().toInstant())
                                ));
                            }
                        }
                    } catch (Exception e) {
                        // Skip files that cause errors
                    }
                    return FileVisitResult.CONTINUE;
                }
            });
        } catch (IOException e) {
            // Return empty list on error
        }
        
        results.sort(Comparator.comparing(FileInfo::getPath));
        return results;
    }
}
