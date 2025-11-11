package com.deepagents.backends.protocol;

import java.util.List;

public interface BackendProtocol {
    
    List<FileInfo> lsInfo(String path);
    
    String read(String filePath, int offset, int limit);
    
    default String read(String filePath) {
        return read(filePath, 0, 2000);
    }
    
    Object grepRaw(String pattern, String path, String glob);
    
    default Object grepRaw(String pattern) {
        return grepRaw(pattern, "/", null);
    }
    
    List<FileInfo> globInfo(String pattern, String path);
    
    default List<FileInfo> globInfo(String pattern) {
        return globInfo(pattern, "/");
    }
    
    WriteResult write(String filePath, String content);
    
    EditResult edit(String filePath, String oldString, String newString, boolean replaceAll);
    
    default EditResult edit(String filePath, String oldString, String newString) {
        return edit(filePath, oldString, newString, false);
    }
}
