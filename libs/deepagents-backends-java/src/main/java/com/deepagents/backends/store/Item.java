package com.deepagents.backends.store;

import java.time.Instant;
import java.util.Arrays;
import java.util.Map;
import java.util.Objects;

public class Item {
    private final Map<String, Object> value;
    private final String key;
    private final String[] namespace;
    private final Instant createdAt;
    private final Instant updatedAt;

    public Item(Map<String, Object> value, String key, String[] namespace, Instant createdAt, Instant updatedAt) {
        this.value = value;
        this.key = key;
        this.namespace = namespace;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Map<String, Object> getValue() {
        return value;
    }

    public String getKey() {
        return key;
    }

    public String[] getNamespace() {
        return namespace;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Item item = (Item) o;
        return Objects.equals(value, item.value) &&
               Objects.equals(key, item.key) &&
               Arrays.equals(namespace, item.namespace) &&
               Objects.equals(createdAt, item.createdAt) &&
               Objects.equals(updatedAt, item.updatedAt);
    }

    @Override
    public int hashCode() {
        int result = Objects.hash(key);
        result = 31 * result + Arrays.hashCode(namespace);
        return result;
    }

    @Override
    public String toString() {
        return "Item{" +
                "value=" + value +
                ", key='" + key + '\'' +
                ", namespace=" + Arrays.toString(namespace) +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}
