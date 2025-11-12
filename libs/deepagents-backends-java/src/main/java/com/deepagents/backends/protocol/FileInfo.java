package com.deepagents.backends.protocol;

import java.util.Objects;

public class FileInfo {
    private final String path;
    private final boolean isDir;
    private final int size;
    private final String modifiedAt;

    public FileInfo(String path, boolean isDir, int size, String modifiedAt) {
        this.path = path;
        this.isDir = isDir;
        this.size = size;
        this.modifiedAt = modifiedAt;
    }

    public FileInfo(String path, boolean isDir) {
        this(path, isDir, 0, "");
    }

    public String getPath() {
        return path;
    }

    public boolean isDir() {
        return isDir;
    }

    public int getSize() {
        return size;
    }

    public String getModifiedAt() {
        return modifiedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        FileInfo fileInfo = (FileInfo) o;
        return isDir == fileInfo.isDir &&
                size == fileInfo.size &&
                Objects.equals(path, fileInfo.path) &&
                Objects.equals(modifiedAt, fileInfo.modifiedAt);
    }

    @Override
    public int hashCode() {
        return Objects.hash(path, isDir, size, modifiedAt);
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
