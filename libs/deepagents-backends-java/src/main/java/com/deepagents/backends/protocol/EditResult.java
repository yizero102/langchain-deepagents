package com.deepagents.backends.protocol;

import java.util.Map;
import java.util.Objects;

public class EditResult {
    private final String error;
    private final String path;
    private final Map<String, Object> filesUpdate;
    private final Integer occurrences;

    public EditResult(String error, String path, Map<String, Object> filesUpdate, Integer occurrences) {
        this.error = error;
        this.path = path;
        this.filesUpdate = filesUpdate;
        this.occurrences = occurrences;
    }

    public static EditResult error(String error) {
        return new EditResult(error, null, null, null);
    }

    public static EditResult success(String path, int occurrences) {
        return new EditResult(null, path, null, occurrences);
    }

    public static EditResult successWithUpdate(String path, Map<String, Object> filesUpdate, int occurrences) {
        return new EditResult(null, path, filesUpdate, occurrences);
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

    public Integer getOccurrences() {
        return occurrences;
    }

    public boolean isSuccess() {
        return error == null;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        EditResult that = (EditResult) o;
        return Objects.equals(error, that.error) &&
                Objects.equals(path, that.path) &&
                Objects.equals(filesUpdate, that.filesUpdate) &&
                Objects.equals(occurrences, that.occurrences);
    }

    @Override
    public int hashCode() {
        return Objects.hash(error, path, filesUpdate, occurrences);
    }

    @Override
    public String toString() {
        return "EditResult{" +
                "error='" + error + '\'' +
                ", path='" + path + '\'' +
                ", filesUpdate=" + filesUpdate +
                ", occurrences=" + occurrences +
                '}';
    }
}
