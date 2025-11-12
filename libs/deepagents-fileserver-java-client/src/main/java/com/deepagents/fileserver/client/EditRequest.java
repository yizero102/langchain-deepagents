package com.deepagents.fileserver.client;

/**
 * Edit file request model.
 */
public class EditRequest {
    private String filePath;
    private String oldString;
    private String newString;
    private boolean replaceAll;

    public EditRequest() {
    }

    public EditRequest(String filePath, String oldString, String newString, boolean replaceAll) {
        this.filePath = filePath;
        this.oldString = oldString;
        this.newString = newString;
        this.replaceAll = replaceAll;
    }

    public String getFilePath() {
        return filePath;
    }

    public void setFilePath(String filePath) {
        this.filePath = filePath;
    }

    public String getOldString() {
        return oldString;
    }

    public void setOldString(String oldString) {
        this.oldString = oldString;
    }

    public String getNewString() {
        return newString;
    }

    public void setNewString(String newString) {
        this.newString = newString;
    }

    public boolean isReplaceAll() {
        return replaceAll;
    }

    public void setReplaceAll(boolean replaceAll) {
        this.replaceAll = replaceAll;
    }
}
