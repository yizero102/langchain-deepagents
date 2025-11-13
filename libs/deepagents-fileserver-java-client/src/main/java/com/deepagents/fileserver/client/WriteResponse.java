package com.deepagents.fileserver.client;

/**
 * Write file response model.
 */
public class WriteResponse {
    private String error;
    private String path;

    public WriteResponse() {
    }

    public WriteResponse(String error, String path) {
        this.error = error;
        this.path = path;
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

    @Override
    public String toString() {
        return "WriteResponse{" +
                "error='" + error + '\'' +
                ", path='" + path + '\'' +
                '}';
    }
}
