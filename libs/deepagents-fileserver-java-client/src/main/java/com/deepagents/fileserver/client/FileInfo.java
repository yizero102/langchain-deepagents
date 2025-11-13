package com.deepagents.fileserver.client;

/**
 * File information model.
 */
public class FileInfo {
    private String path;
    private boolean isDir;
    private Integer size;
    private String modifiedAt;

    public FileInfo() {
    }

    public FileInfo(String path, boolean isDir, Integer size, String modifiedAt) {
        this.path = path;
        this.isDir = isDir;
        this.size = size;
        this.modifiedAt = modifiedAt;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public boolean isDir() {
        return isDir;
    }

    public void setDir(boolean dir) {
        isDir = dir;
    }

    public Integer getSize() {
        return size;
    }

    public void setSize(Integer size) {
        this.size = size;
    }

    public String getModifiedAt() {
        return modifiedAt;
    }

    public void setModifiedAt(String modifiedAt) {
        this.modifiedAt = modifiedAt;
    }

    @Override
    public String toString() {
        return "FileInfo{" +
                "path='" + path + '\'' +
                ", isDir=" + isDir +
                ", size=" + size +
                ", modifiedAt='" + modifiedAt + '\'' +
                '}';
    }
}
