package com.deepagents.backends.utils;

import java.util.List;
import java.util.Objects;

public class FileData {
    private final List<String> content;
    private final String createdAt;
    private final String modifiedAt;

    public FileData(List<String> content, String createdAt, String modifiedAt) {
        this.content = content;
        this.createdAt = createdAt;
        this.modifiedAt = modifiedAt;
    }

    public List<String> getContent() {
        return content;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public String getModifiedAt() {
        return modifiedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        FileData fileData = (FileData) o;
        return Objects.equals(content, fileData.content) &&
                Objects.equals(createdAt, fileData.createdAt) &&
                Objects.equals(modifiedAt, fileData.modifiedAt);
    }

    @Override
    public int hashCode() {
        return Objects.hash(content, createdAt, modifiedAt);
    }

    @Override
    public String toString() {
        return "FileData{" +
                "content=" + content +
                ", createdAt='" + createdAt + '\'' +
                ", modifiedAt='" + modifiedAt + '\'' +
                '}';
    }
}
