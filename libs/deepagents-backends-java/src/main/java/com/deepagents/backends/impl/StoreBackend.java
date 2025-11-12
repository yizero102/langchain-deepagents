package com.deepagents.backends.impl;

import com.deepagents.backends.protocol.*;
import com.deepagents.backends.store.Item;
import com.deepagents.backends.store.Store;
import com.deepagents.backends.utils.BackendUtils;
import com.deepagents.backends.utils.FileData;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

public class StoreBackend implements BackendProtocol {
    
    private final Store store;
    private final String[] namespace;
    
    public StoreBackend(Store store) {
        this(store, new String[]{"filesystem"});
    }
    
    public StoreBackend(Store store, String[] namespace) {
        this.store = store;
        this.namespace = namespace;
    }
    
    public Store getStore() {
        return store;
    }
    
    public String[] getNamespace() {
        return namespace;
    }
    
    private FileData convertStoreItemToFileData(Item storeItem) {
        Map<String, Object> value = storeItem.getValue();
        
        if (!value.containsKey("content") || !(value.get("content") instanceof List)) {
            throw new IllegalArgumentException("Store item does not contain valid content field");
        }
        if (!value.containsKey("created_at") || !(value.get("created_at") instanceof String)) {
            throw new IllegalArgumentException("Store item does not contain valid created_at field");
        }
        if (!value.containsKey("modified_at") || !(value.get("modified_at") instanceof String)) {
            throw new IllegalArgumentException("Store item does not contain valid modified_at field");
        }
        
        @SuppressWarnings("unchecked")
        List<String> content = (List<String>) value.get("content");
        String createdAt = (String) value.get("created_at");
        String modifiedAt = (String) value.get("modified_at");
        
        return new FileData(content, createdAt, modifiedAt);
    }
    
    private Map<String, Object> convertFileDataToStoreValue(FileData fileData) {
        Map<String, Object> value = new HashMap<>();
        value.put("content", fileData.getContent());
        value.put("created_at", fileData.getCreatedAt());
        value.put("modified_at", fileData.getModifiedAt());
        return value;
    }
    
    private List<Item> searchStorePaginated(Store store, String[] namespace) {
        List<Item> allItems = new ArrayList<>();
        int pageSize = 100;
        int offset = 0;
        
        while (true) {
            List<Item> pageItems = store.search(namespace, null, pageSize, offset);
            if (pageItems.isEmpty()) {
                break;
            }
            allItems.addAll(pageItems);
            if (pageItems.size() < pageSize) {
                break;
            }
            offset += pageSize;
        }
        
        return allItems;
    }

    @Override
    public List<FileInfo> lsInfo(String path) {
        List<Item> items = searchStorePaginated(store, namespace);
        List<FileInfo> infos = new ArrayList<>();
        Set<String> subdirs = new HashSet<>();
        
        String normalizedPath = path.endsWith("/") ? path : path + "/";
        
        for (Item item : items) {
            String k = item.getKey();
            
            if (!k.startsWith(normalizedPath)) {
                continue;
            }
            
            String relative = k.substring(normalizedPath.length());
            
            if (relative.contains("/")) {
                String subdirName = relative.split("/")[0];
                subdirs.add(normalizedPath + subdirName + "/");
                continue;
            }
            
            try {
                FileData fd = convertStoreItemToFileData(item);
                int size = String.join("\n", fd.getContent()).length();
                infos.add(new FileInfo(k, false, size, fd.getModifiedAt()));
            } catch (IllegalArgumentException e) {
                continue;
            }
        }
        
        for (String subdir : subdirs) {
            infos.add(new FileInfo(subdir, true, 0, ""));
        }
        
        infos.sort(Comparator.comparing(FileInfo::getPath));
        return infos;
    }

    @Override
    public String read(String filePath, int offset, int limit) {
        Item item = store.get(namespace, filePath);
        
        if (item == null) {
            return String.format("Error: File '%s' not found", filePath);
        }
        
        try {
            FileData fileData = convertStoreItemToFileData(item);
            return BackendUtils.formatReadResponse(fileData, offset, limit);
        } catch (IllegalArgumentException e) {
            return "Error: " + e.getMessage();
        }
    }

    @Override
    public WriteResult write(String filePath, String content) {
        Item existing = store.get(namespace, filePath);
        
        if (existing != null) {
            return WriteResult.error(String.format("Cannot write to %s because it already exists. Read and then make an edit, or write to a new path.", filePath));
        }
        
        FileData fileData = BackendUtils.createFileData(content);
        Map<String, Object> storeValue = convertFileDataToStoreValue(fileData);
        store.put(namespace, filePath, storeValue);
        
        return WriteResult.success(filePath);
    }

    @Override
    public EditResult edit(String filePath, String oldString, String newString, boolean replaceAll) {
        Item item = store.get(namespace, filePath);
        
        if (item == null) {
            return EditResult.error(String.format("Error: File '%s' not found", filePath));
        }
        
        try {
            FileData fileData = convertStoreItemToFileData(item);
            String content = BackendUtils.fileDataToString(fileData);
            Object result = BackendUtils.performStringReplacement(content, oldString, newString, replaceAll);
            
            if (result instanceof String) {
                return EditResult.error((String) result);
            }
            
            BackendUtils.ReplacementResult replacement = (BackendUtils.ReplacementResult) result;
            FileData newFileData = BackendUtils.updateFileData(fileData, replacement.getNewContent());
            Map<String, Object> storeValue = convertFileDataToStoreValue(newFileData);
            store.put(namespace, filePath, storeValue);
            
            return EditResult.success(filePath, replacement.getOccurrences());
        } catch (IllegalArgumentException e) {
            return EditResult.error("Error: " + e.getMessage());
        }
    }

    @Override
    public Object grepRaw(String pattern, String path, String glob) {
        List<Item> items = searchStorePaginated(store, namespace);
        Map<String, FileData> files = new HashMap<>();
        
        for (Item item : items) {
            try {
                FileData fileData = convertStoreItemToFileData(item);
                files.put(item.getKey(), fileData);
            } catch (IllegalArgumentException e) {
                continue;
            }
        }
        
        try {
            return BackendUtils.grepMatchesFromFiles(files, pattern, path, glob);
        } catch (IllegalArgumentException e) {
            return e.getMessage();
        }
    }

    @Override
    public List<FileInfo> globInfo(String pattern, String path) {
        List<Item> items = searchStorePaginated(store, namespace);
        Map<String, FileData> files = new HashMap<>();
        
        for (Item item : items) {
            try {
                FileData fileData = convertStoreItemToFileData(item);
                files.put(item.getKey(), fileData);
            } catch (IllegalArgumentException e) {
                continue;
            }
        }
        
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
}
