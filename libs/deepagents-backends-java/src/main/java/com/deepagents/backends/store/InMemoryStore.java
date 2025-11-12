package com.deepagents.backends.store;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

public class InMemoryStore implements Store {
    
    private final Map<String, Map<String, Item>> data;
    
    public InMemoryStore() {
        this.data = new HashMap<>();
    }
    
    private String namespaceToString(String[] namespace) {
        return String.join(":", namespace);
    }
    
    private boolean namespaceStartsWith(String[] namespace, String[] prefix) {
        if (namespace.length < prefix.length) {
            return false;
        }
        for (int i = 0; i < prefix.length; i++) {
            if (!namespace[i].equals(prefix[i])) {
                return false;
            }
        }
        return true;
    }
    
    @Override
    public Item get(String[] namespace, String key) {
        String nsKey = namespaceToString(namespace);
        Map<String, Item> nsData = data.get(nsKey);
        if (nsData == null) {
            return null;
        }
        return nsData.get(key);
    }
    
    @Override
    public void put(String[] namespace, String key, Map<String, Object> value) {
        String nsKey = namespaceToString(namespace);
        data.putIfAbsent(nsKey, new HashMap<>());
        
        Instant now = Instant.now();
        Item item = new Item(value, key, namespace, now, now);
        data.get(nsKey).put(key, item);
    }
    
    @Override
    public List<Item> search(String[] namespacePrefix, Map<String, Object> filter, int limit, int offset) {
        List<Item> results = new ArrayList<>();
        
        for (Map.Entry<String, Map<String, Item>> entry : data.entrySet()) {
            for (Item item : entry.getValue().values()) {
                if (namespaceStartsWith(item.getNamespace(), namespacePrefix)) {
                    if (filter == null || matchesFilter(item, filter)) {
                        results.add(item);
                    }
                }
            }
        }
        
        results.sort(Comparator.comparing(Item::getKey));
        
        int fromIndex = Math.min(offset, results.size());
        int toIndex = Math.min(offset + limit, results.size());
        
        return results.subList(fromIndex, toIndex);
    }
    
    private boolean matchesFilter(Item item, Map<String, Object> filter) {
        for (Map.Entry<String, Object> filterEntry : filter.entrySet()) {
            String key = filterEntry.getKey();
            Object filterValue = filterEntry.getValue();
            Object itemValue = item.getValue().get(key);
            
            if (!Objects.equals(itemValue, filterValue)) {
                return false;
            }
        }
        return true;
    }
}
