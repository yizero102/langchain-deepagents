package com.deepagents.fileserver.client;

/**
 * Write file request model.
 */
public class WriteRequest {
    private String filePath;
    private String content;

    public WriteRequest() {
    }

    public WriteRequest(String filePath, String content) {
        this.filePath = filePath;
        this.content = content;
    }

    public String getFilePath() {
        return filePath;
    }

    public void setFilePath(String filePath) {
        this.filePath = filePath;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }
}
