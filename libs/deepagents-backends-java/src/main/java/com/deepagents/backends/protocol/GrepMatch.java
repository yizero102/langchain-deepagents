package com.deepagents.backends.protocol;

import java.util.Objects;

public class GrepMatch {
    private final String path;
    private final int line;
    private final String text;

    public GrepMatch(String path, int line, String text) {
        this.path = path;
        this.line = line;
        this.text = text;
    }

    public String getPath() {
        return path;
    }

    public int getLine() {
        return line;
    }

    public String getText() {
        return text;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        GrepMatch grepMatch = (GrepMatch) o;
        return line == grepMatch.line &&
                Objects.equals(path, grepMatch.path) &&
                Objects.equals(text, grepMatch.text);
    }

    @Override
    public int hashCode() {
        return Objects.hash(path, line, text);
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
