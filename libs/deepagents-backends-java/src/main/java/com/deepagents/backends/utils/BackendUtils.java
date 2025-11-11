package com.deepagents.backends.utils;

import com.deepagents.backends.protocol.GrepMatch;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;
import java.util.stream.Collectors;

public class BackendUtils {
    
    public static final String EMPTY_CONTENT_WARNING = "System reminder: File exists but has empty contents";
    public static final int MAX_LINE_LENGTH = 10000;
    public static final int LINE_NUMBER_WIDTH = 6;
    public static final int TOOL_RESULT_TOKEN_LIMIT = 20000;
    public static final String TRUNCATION_GUIDANCE = "... [results truncated, try being more specific with your parameters]";

    public static String getCurrentISOTimestamp() {
        return Instant.now().atOffset(ZoneOffset.UTC).format(DateTimeFormatter.ISO_INSTANT);
    }

    public static FileData createFileData(String content, String createdAt) {
        List<String> lines = Arrays.asList(content.split("\n", -1));
        String timestamp = createdAt != null ? createdAt : getCurrentISOTimestamp();
        return new FileData(lines, timestamp, getCurrentISOTimestamp());
    }

    public static FileData createFileData(String content) {
        return createFileData(content, null);
    }

    public static FileData updateFileData(FileData oldData, String content) {
        List<String> lines = Arrays.asList(content.split("\n", -1));
        return new FileData(lines, oldData.getCreatedAt(), getCurrentISOTimestamp());
    }

    public static String fileDataToString(FileData fileData) {
        return String.join("\n", fileData.getContent());
    }

    public static String checkEmptyContent(String content) {
        if (content == null || content.trim().isEmpty()) {
            return EMPTY_CONTENT_WARNING;
        }
        return null;
    }

    public static String formatContentWithLineNumbers(List<String> lines, int startLine) {
        List<String> resultLines = new ArrayList<>();
        
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i);
            int lineNum = i + startLine;
            
            if (line.length() <= MAX_LINE_LENGTH) {
                resultLines.add(String.format("%" + LINE_NUMBER_WIDTH + "d\t%s", lineNum, line));
            } else {
                int numChunks = (line.length() + MAX_LINE_LENGTH - 1) / MAX_LINE_LENGTH;
                for (int chunkIdx = 0; chunkIdx < numChunks; chunkIdx++) {
                    int start = chunkIdx * MAX_LINE_LENGTH;
                    int end = Math.min(start + MAX_LINE_LENGTH, line.length());
                    String chunk = line.substring(start, end);
                    
                    if (chunkIdx == 0) {
                        resultLines.add(String.format("%" + LINE_NUMBER_WIDTH + "d\t%s", lineNum, chunk));
                    } else {
                        String continuationMarker = lineNum + "." + chunkIdx;
                        resultLines.add(String.format("%" + LINE_NUMBER_WIDTH + "s\t%s", continuationMarker, chunk));
                    }
                }
            }
        }
        
        return String.join("\n", resultLines);
    }

    public static String formatReadResponse(FileData fileData, int offset, int limit) {
        String content = fileDataToString(fileData);
        String emptyMsg = checkEmptyContent(content);
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
        return formatContentWithLineNumbers(selectedLines, startIdx + 1);
    }

    public static class ReplacementResult {
        private final String newContent;
        private final int occurrences;
        
        public ReplacementResult(String newContent, int occurrences) {
            this.newContent = newContent;
            this.occurrences = occurrences;
        }
        
        public String getNewContent() {
            return newContent;
        }
        
        public int getOccurrences() {
            return occurrences;
        }
    }

    public static Object performStringReplacement(String content, String oldString, String newString, boolean replaceAll) {
        int occurrences = countOccurrences(content, oldString);
        
        if (occurrences == 0) {
            return String.format("Error: String not found in file: '%s'", oldString);
        }
        
        if (occurrences > 1 && !replaceAll) {
            return String.format("Error: String '%s' appears %d times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context.", 
                    oldString, occurrences);
        }
        
        String newContent = content.replace(oldString, newString);
        return new ReplacementResult(newContent, occurrences);
    }

    private static int countOccurrences(String text, String pattern) {
        int count = 0;
        int index = 0;
        while ((index = text.indexOf(pattern, index)) != -1) {
            count++;
            index += pattern.length();
        }
        return count;
    }

    public static String validatePath(String path) {
        if (path == null || path.trim().isEmpty()) {
            throw new IllegalArgumentException("Path cannot be empty");
        }
        
        String normalized = path.startsWith("/") ? path : "/" + path;
        
        if (!normalized.endsWith("/")) {
            normalized += "/";
        }
        
        return normalized;
    }

    public static List<GrepMatch> grepMatchesFromFiles(Map<String, FileData> files, String pattern, String path, String glob) {
        Pattern regex;
        try {
            regex = Pattern.compile(pattern);
        } catch (PatternSyntaxException e) {
            throw new IllegalArgumentException("Invalid regex pattern: " + e.getMessage());
        }
        
        String normalizedPath;
        try {
            normalizedPath = validatePath(path);
        } catch (IllegalArgumentException e) {
            return new ArrayList<>();
        }
        
        Map<String, FileData> filtered = files.entrySet().stream()
                .filter(e -> e.getKey().startsWith(normalizedPath))
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
        
        if (glob != null && !glob.isEmpty()) {
            filtered = filtered.entrySet().stream()
                    .filter(e -> matchesGlob(getFileName(e.getKey()), glob))
                    .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
        }
        
        List<GrepMatch> matches = new ArrayList<>();
        for (Map.Entry<String, FileData> entry : filtered.entrySet()) {
            String filePath = entry.getKey();
            FileData fileData = entry.getValue();
            
            List<String> content = fileData.getContent();
            for (int i = 0; i < content.size(); i++) {
                String line = content.get(i);
                Matcher matcher = regex.matcher(line);
                if (matcher.find()) {
                    matches.add(new GrepMatch(filePath, i + 1, line));
                }
            }
        }
        
        return matches;
    }

    private static String getFileName(String path) {
        int lastSlash = path.lastIndexOf('/');
        return lastSlash >= 0 ? path.substring(lastSlash + 1) : path;
    }

    private static boolean matchesGlob(String filename, String glob) {
        String regexPattern = glob
                .replace(".", "\\.")
                .replace("*", ".*")
                .replace("?", ".");
        return filename.matches(regexPattern);
    }

    public static String globSearchFiles(Map<String, FileData> files, String pattern, String path) {
        String normalizedPath;
        try {
            normalizedPath = validatePath(path);
        } catch (IllegalArgumentException e) {
            return "No files found";
        }
        
        Map<String, FileData> filtered = files.entrySet().stream()
                .filter(e -> e.getKey().startsWith(normalizedPath))
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
        
        List<Map.Entry<String, FileData>> matches = new ArrayList<>();
        for (Map.Entry<String, FileData> entry : filtered.entrySet()) {
            String filePath = entry.getKey();
            String relative = filePath.substring(normalizedPath.length());
            if (relative.startsWith("/")) {
                relative = relative.substring(1);
            }
            if (relative.isEmpty()) {
                String[] parts = filePath.split("/");
                relative = parts[parts.length - 1];
            }
            
            if (matchesGlob(relative, pattern) || matchesRecursiveGlob(relative, pattern)) {
                matches.add(entry);
            }
        }
        
        matches.sort((a, b) -> b.getValue().getModifiedAt().compareTo(a.getValue().getModifiedAt()));
        
        if (matches.isEmpty()) {
            return "No files found";
        }
        
        return matches.stream()
                .map(Map.Entry::getKey)
                .collect(Collectors.joining("\n"));
    }

    private static boolean matchesRecursiveGlob(String path, String pattern) {
        if (pattern.contains("**")) {
            String[] patternParts = pattern.split("/");
            String[] pathParts = path.split("/");
            return matchesRecursivePattern(pathParts, 0, patternParts, 0);
        }
        return matchesGlob(path, pattern);
    }

    private static boolean matchesRecursivePattern(String[] pathParts, int pathIdx, String[] patternParts, int patternIdx) {
        if (patternIdx >= patternParts.length) {
            return pathIdx >= pathParts.length;
        }
        
        if (pathIdx >= pathParts.length) {
            for (int i = patternIdx; i < patternParts.length; i++) {
                if (!patternParts[i].equals("**")) {
                    return false;
                }
            }
            return true;
        }
        
        String pattern = patternParts[patternIdx];
        if (pattern.equals("**")) {
            if (patternIdx == patternParts.length - 1) {
                return true;
            }
            for (int i = pathIdx; i <= pathParts.length; i++) {
                if (matchesRecursivePattern(pathParts, i, patternParts, patternIdx + 1)) {
                    return true;
                }
            }
            return false;
        }
        
        if (matchesGlob(pathParts[pathIdx], pattern)) {
            return matchesRecursivePattern(pathParts, pathIdx + 1, patternParts, patternIdx + 1);
        }
        
        return false;
    }
}
