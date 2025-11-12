package com.deepagents.backends.impl;

import com.deepagents.backends.protocol.*;
import com.deepagents.backends.utils.BackendUtils;
import com.deepagents.backends.utils.FileData;

import java.util.*;
import java.util.stream.Collectors;

public class StateBackend implements BackendProtocol {
    
    private final Map<String, FileData> files;
    
    public StateBackend() {
        this.files = new HashMap<>();
    }
    
    public StateBackend(Map<String, FileData> files) {
        this.files = files;
    }
    
    public Map<String, FileData> getFiles() {
        return files;
    }

    @Override
    public List<FileInfo> lsInfo(String path) {
        List<FileInfo> infos = new ArrayList<>();
        Set<String> subdirs = new HashSet<>();
        
        String normalizedPath = path.endsWith("/") ? path : path + "/";
        
        for (Map.Entry<String, FileData> entry : files.entrySet()) {
            String k = entry.getKey();
            FileData fd = entry.getValue();
            
            if (!k.startsWith(normalizedPath)) {
                continue;
            }
            
            String relative = k.substring(normalizedPath.length());
            
            if (relative.contains("/")) {
                String subdirName = relative.split("/")[0];
                subdirs.add(normalizedPath + subdirName + "/");
                continue;
            }
            
            int size = String.join("\n", fd.getContent()).length();
            infos.add(new FileInfo(k, false, size, fd.getModifiedAt()));
        }
        
        for (String subdir : subdirs) {
            infos.add(new FileInfo(subdir, true, 0, ""));
        }
        
        infos.sort(Comparator.comparing(FileInfo::getPath));
        return infos;
    }

    @Override
    public String read(String filePath, int offset, int limit) {
        FileData fileData = files.get(filePath);
        
        if (fileData == null) {
            return String.format("Error: File '%s' not found", filePath);
        }
        
        return BackendUtils.formatReadResponse(fileData, offset, limit);
    }

    @Override
    public Object grepRaw(String pattern, String path, String glob) {
        try {
            return BackendUtils.grepMatchesFromFiles(files, pattern, path, glob);
        } catch (IllegalArgumentException e) {
            return e.getMessage();
        }
    }

    @Override
    public List<FileInfo> globInfo(String pattern, String path) {
        String result = BackendUtils.globSearchFiles(files, pattern, path);
        if (result.equals("No files found")) {
            return new ArrayList<>();
        }
        
        String[] paths = result.split("\n");
        List<FileInfo> infos = new ArrayList<>();
        
        for (String p : paths) {
            FileData fd = files.get(p);
            int size = fd != null ? String.join("\n", fd.getContent()).length() : 0;
            String modifiedAt = fd != null ? fd.getModifiedAt() : "";
            infos.add(new FileInfo(p, false, size, modifiedAt));
        }
        
        return infos;
    }

    @Override
    public WriteResult write(String filePath, String content) {
        if (files.containsKey(filePath)) {
            return WriteResult.error(String.format("Cannot write to %s because it already exists. Read and then make an edit, or write to a new path.", filePath));
        }
        
        FileData newFileData = BackendUtils.createFileData(content);
        files.put(filePath, newFileData);
        
        Map<String, Object> filesUpdate = new HashMap<>();
        filesUpdate.put(filePath, newFileData);
        
        return WriteResult.successWithUpdate(filePath, filesUpdate);
    }

    @Override
    public EditResult edit(String filePath, String oldString, String newString, boolean replaceAll) {
        FileData fileData = files.get(filePath);
        
        if (fileData == null) {
            return EditResult.error(String.format("Error: File '%s' not found", filePath));
        }
        
        String content = BackendUtils.fileDataToString(fileData);
        Object result = BackendUtils.performStringReplacement(content, oldString, newString, replaceAll);
        
        if (result instanceof String) {
            return EditResult.error((String) result);
        }
        
        BackendUtils.ReplacementResult replacement = (BackendUtils.ReplacementResult) result;
        FileData newFileData = BackendUtils.updateFileData(fileData, replacement.getNewContent());
        files.put(filePath, newFileData);
        
        Map<String, Object> filesUpdate = new HashMap<>();
        filesUpdate.put(filePath, newFileData);
        
        return EditResult.successWithUpdate(filePath, filesUpdate, replacement.getOccurrences());
    }
}
