package com.deepagents.backends.impl;

import com.deepagents.backends.protocol.*;

import java.util.*;
import java.util.stream.Collectors;

public class CompositeBackend implements BackendProtocol {
    
    private final BackendProtocol defaultBackend;
    private final Map<String, BackendProtocol> routes;
    private final List<Map.Entry<String, BackendProtocol>> sortedRoutes;
    
    public CompositeBackend(BackendProtocol defaultBackend, Map<String, BackendProtocol> routes) {
        this.defaultBackend = defaultBackend;
        this.routes = routes;
        this.sortedRoutes = routes.entrySet().stream()
                .sorted((a, b) -> Integer.compare(b.getKey().length(), a.getKey().length()))
                .collect(Collectors.toList());
    }
    
    private Map.Entry<BackendProtocol, String> getBackendAndKey(String key) {
        for (Map.Entry<String, BackendProtocol> entry : sortedRoutes) {
            String prefix = entry.getKey();
            if (key.startsWith(prefix)) {
                String suffix = key.substring(prefix.length());
                String strippedKey = suffix.isEmpty() ? "/" : "/" + suffix;
                return Map.entry(entry.getValue(), strippedKey);
            }
        }
        return Map.entry(defaultBackend, key);
    }

    @Override
    public List<FileInfo> lsInfo(String path) {
        for (Map.Entry<String, BackendProtocol> entry : sortedRoutes) {
            String routePrefix = entry.getKey();
            if (path.startsWith(routePrefix.substring(0, routePrefix.length() - 1))) {
                String suffix = path.substring(routePrefix.length());
                String searchPath = suffix.isEmpty() ? "/" : "/" + suffix;
                List<FileInfo> infos = entry.getValue().lsInfo(searchPath);
                return infos.stream()
                        .map(fi -> new FileInfo(
                                routePrefix.substring(0, routePrefix.length() - 1) + fi.getPath(),
                                fi.isDir(),
                                fi.getSize(),
                                fi.getModifiedAt()
                        ))
                        .collect(Collectors.toList());
            }
        }
        
        if (path.equals("/")) {
            List<FileInfo> results = new ArrayList<>(defaultBackend.lsInfo(path));
            for (Map.Entry<String, BackendProtocol> entry : sortedRoutes) {
                results.add(new FileInfo(entry.getKey(), true, 0, ""));
            }
            results.sort(Comparator.comparing(FileInfo::getPath));
            return results;
        }
        
        return defaultBackend.lsInfo(path);
    }

    @Override
    public String read(String filePath, int offset, int limit) {
        Map.Entry<BackendProtocol, String> entry = getBackendAndKey(filePath);
        return entry.getKey().read(entry.getValue(), offset, limit);
    }

    @Override
    public Object grepRaw(String pattern, String path, String glob) {
        for (Map.Entry<String, BackendProtocol> entry : sortedRoutes) {
            String routePrefix = entry.getKey();
            if (path != null && path.startsWith(routePrefix.substring(0, routePrefix.length() - 1))) {
                String searchPath = path.substring(routePrefix.length() - 1);
                Object raw = entry.getValue().grepRaw(pattern, searchPath.isEmpty() ? "/" : searchPath, glob);
                if (raw instanceof String) {
                    return raw;
                }
                @SuppressWarnings("unchecked")
                List<GrepMatch> matches = (List<GrepMatch>) raw;
                return matches.stream()
                        .map(m -> new GrepMatch(
                                routePrefix.substring(0, routePrefix.length() - 1) + m.getPath(),
                                m.getLine(),
                                m.getText()
                        ))
                        .collect(Collectors.toList());
            }
        }
        
        List<GrepMatch> allMatches = new ArrayList<>();
        Object rawDefault = defaultBackend.grepRaw(pattern, path, glob);
        if (rawDefault instanceof String) {
            return rawDefault;
        }
        @SuppressWarnings("unchecked")
        List<GrepMatch> defaultMatches = (List<GrepMatch>) rawDefault;
        allMatches.addAll(defaultMatches);
        
        for (Map.Entry<String, BackendProtocol> entry : routes.entrySet()) {
            Object raw = entry.getValue().grepRaw(pattern, "/", glob);
            if (raw instanceof String) {
                return raw;
            }
            @SuppressWarnings("unchecked")
            List<GrepMatch> matches = (List<GrepMatch>) raw;
            String prefix = entry.getKey().substring(0, entry.getKey().length() - 1);
            allMatches.addAll(matches.stream()
                    .map(m -> new GrepMatch(prefix + m.getPath(), m.getLine(), m.getText()))
                    .collect(Collectors.toList()));
        }
        
        return allMatches;
    }

    @Override
    public List<FileInfo> globInfo(String pattern, String path) {
        List<FileInfo> results = new ArrayList<>();
        
        for (Map.Entry<String, BackendProtocol> entry : sortedRoutes) {
            String routePrefix = entry.getKey();
            if (path.startsWith(routePrefix.substring(0, routePrefix.length() - 1))) {
                String searchPath = path.substring(routePrefix.length() - 1);
                List<FileInfo> infos = entry.getValue().globInfo(pattern, searchPath.isEmpty() ? "/" : searchPath);
                return infos.stream()
                        .map(fi -> new FileInfo(
                                routePrefix.substring(0, routePrefix.length() - 1) + fi.getPath(),
                                fi.isDir(),
                                fi.getSize(),
                                fi.getModifiedAt()
                        ))
                        .collect(Collectors.toList());
            }
        }
        
        results.addAll(defaultBackend.globInfo(pattern, path));
        
        for (Map.Entry<String, BackendProtocol> entry : routes.entrySet()) {
            List<FileInfo> infos = entry.getValue().globInfo(pattern, "/");
            String prefix = entry.getKey().substring(0, entry.getKey().length() - 1);
            results.addAll(infos.stream()
                    .map(fi -> new FileInfo(prefix + fi.getPath(), fi.isDir(), fi.getSize(), fi.getModifiedAt()))
                    .collect(Collectors.toList()));
        }
        
        results.sort(Comparator.comparing(FileInfo::getPath));
        return results;
    }

    @Override
    public WriteResult write(String filePath, String content) {
        Map.Entry<BackendProtocol, String> entry = getBackendAndKey(filePath);
        return entry.getKey().write(entry.getValue(), content);
    }

    @Override
    public EditResult edit(String filePath, String oldString, String newString, boolean replaceAll) {
        Map.Entry<BackendProtocol, String> entry = getBackendAndKey(filePath);
        return entry.getKey().edit(entry.getValue(), oldString, newString, replaceAll);
    }
}
