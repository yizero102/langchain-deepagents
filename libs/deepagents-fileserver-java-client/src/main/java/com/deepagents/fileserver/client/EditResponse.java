package com.deepagents.fileserver.client;

/**
 * Edit file response model.
 */
public class EditResponse {
    private String error;
    private String path;
    private Integer occurrences;

    public EditResponse() {
    }

    public EditResponse(String error, String path, Integer occurrences) {
        this.error = error;
        this.path = path;
        this.occurrences = occurrences;
    }

    public String getError() {
        return error;
    }

    public void setError(String error) {
        this.error = error;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public Integer getOccurrences() {
        return occurrences;
    }

    public void setOccurrences(Integer occurrences) {
        this.occurrences = occurrences;
    }

    @Override
    public String toString() {
        return "EditResponse{" +
                "error='" + error + '\'' +
                ", path='" + path + '\'' +
                ", occurrences=" + occurrences +
                '}';
    }
}
