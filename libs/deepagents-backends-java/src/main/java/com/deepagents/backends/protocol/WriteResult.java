package com.deepagents.backends.protocol;

import java.util.Map;
import java.util.Objects;

public class WriteResult {
    private final String error;
    private final String path;
    private final Map<String, Object> filesUpdate;

    public WriteResult(String error, String path, Map<String, Object> filesUpdate) {
        this.error = error;
        this.path = path;
        this.filesUpdate = filesUpdate;
    }

    public static WriteResult error(String error) {
        return new WriteResult(error, null, null);
    }

    public static WriteResult success(String path) {
        return new WriteResult(null, path, null);
    }

    public static WriteResult successWithUpdate(String path, Map<String, Object> filesUpdate) {
        return new WriteResult(null, path, filesUpdate);
    }

    public String getError() {
        return error;
    }

    public String getPath() {
        return path;
    }

    public Map<String, Object> getFilesUpdate() {
        return filesUpdate;
    }

    public boolean isSuccess() {
        return error == null;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        WriteResult that = (WriteResult) o;
        return Objects.equals(error, that.error) &&
                Objects.equals(path, that.path) &&
                Objects.equals(filesUpdate, that.filesUpdate);
    }

    @Override
    public int hashCode() {
        return Objects.hash(error, path, filesUpdate);
    }

    @Override
    public String toString() {
        return "WriteResult{" +
                "error='" + error + '\'' +
                ", path='" + path + '\'' +
                ", filesUpdate=" + filesUpdate +
                '}';
    }
}
