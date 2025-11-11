package com.deepagents.backends.store;

import java.util.List;
import java.util.Map;

public interface Store {
    
    Item get(String[] namespace, String key);
    
    void put(String[] namespace, String key, Map<String, Object> value);
    
    List<Item> search(String[] namespacePrefix, Map<String, Object> filter, int limit, int offset);
    
    default List<Item> search(String[] namespacePrefix) {
        return search(namespacePrefix, null, 100, 0);
    }
}
