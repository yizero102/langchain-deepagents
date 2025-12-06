package com.deepagents.fileserver.client;

/**
 * Grep match model.
 */
public class GrepMatch {
    private String path;
    private int line;
    private String text;

    public GrepMatch() {
    }

    public GrepMatch(String path, int line, String text) {
        this.path = path;
        this.line = line;
        this.text = text;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public int getLine() {
        return line;
    }

    public void setLine(int line) {
        this.line = line;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    @Override
    public String toString() {
        return "GrepMatch{" +
                "path='" + path + '\'' +
                ", line=" + line +
                ", text='" + text + '\'' +
                '}';
    }
}
