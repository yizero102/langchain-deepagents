package com.deepagents.backends.impl;

import com.deepagents.backends.protocol.*;
import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

public class SandboxBackend implements BackendProtocol {
    
    private final String baseUrl;
    private final String apiKey;
    private final HttpClient httpClient;
    private final Gson gson;
    
    public SandboxBackend(String baseUrl) {
        this(baseUrl, null);
    }
    
    public SandboxBackend(String baseUrl, String apiKey) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.apiKey = apiKey;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        this.gson = new Gson();
    }
    
    private String encodeParam(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }
    
    private HttpRequest.Builder createRequestBuilder(String url) {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(30));
        
        if (apiKey != null && !apiKey.isEmpty()) {
            builder.header("X-API-Key", apiKey);
        }
        
        return builder;
    }
    
    private String sendGetRequest(String url) throws IOException, InterruptedException {
        HttpRequest request = createRequestBuilder(url)
                .GET()
                .build();
        
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        
        if (response.statusCode() >= 400) {
            throw new IOException("HTTP request failed with status: " + response.statusCode() + ", body: " + response.body());
        }
        
        return response.body();
    }
    
    private String sendPostRequest(String url, String jsonBody) throws IOException, InterruptedException {
        HttpRequest request = createRequestBuilder(url)
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .header("Content-Type", "application/json")
                .build();
        
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        
        if (response.statusCode() >= 400) {
            throw new IOException("HTTP request failed with status: " + response.statusCode() + ", body: " + response.body());
        }
        
        return response.body();
    }

    @Override
    public List<FileInfo> lsInfo(String path) {
        try {
            String url = baseUrl + "/api/ls?path=" + encodeParam(path);
            String responseBody = sendGetRequest(url);
            
            JsonObject jsonResponse = JsonParser.parseString(responseBody).getAsJsonObject();
            JsonArray filesArray = jsonResponse.getAsJsonArray("files");
            
            List<FileInfo> fileInfos = new ArrayList<>();
            for (int i = 0; i < filesArray.size(); i++) {
                JsonObject fileObj = filesArray.get(i).getAsJsonObject();
                String filePath = fileObj.get("path").getAsString();
                boolean isDir = fileObj.get("is_dir").getAsBoolean();
                int size = fileObj.has("size") ? fileObj.get("size").getAsInt() : 0;
                String modifiedAt = fileObj.has("modified_at") ? fileObj.get("modified_at").getAsString() : "";
                fileInfos.add(new FileInfo(filePath, isDir, size, modifiedAt));
            }
            
            return fileInfos;
        } catch (Exception e) {
            throw new RuntimeException("Failed to list directory: " + path, e);
        }
    }

    @Override
    public String read(String filePath, int offset, int limit) {
        try {
            String url = baseUrl + "/api/read?file_path=" + encodeParam(filePath) 
                    + "&offset=" + offset + "&limit=" + limit;
            String responseBody = sendGetRequest(url);
            
            JsonObject jsonResponse = JsonParser.parseString(responseBody).getAsJsonObject();
            return jsonResponse.get("content").getAsString();
        } catch (Exception e) {
            return "Error: Failed to read file '" + filePath + "': " + e.getMessage();
        }
    }

    @Override
    public Object grepRaw(String pattern, String path, String glob) {
        try {
            StringBuilder urlBuilder = new StringBuilder(baseUrl + "/api/grep?pattern=" + encodeParam(pattern));
            
            if (path != null && !path.isEmpty()) {
                urlBuilder.append("&path=").append(encodeParam(path));
            }
            
            if (glob != null && !glob.isEmpty()) {
                urlBuilder.append("&glob=").append(encodeParam(glob));
            }
            
            String responseBody = sendGetRequest(urlBuilder.toString());
            
            JsonObject jsonResponse = JsonParser.parseString(responseBody).getAsJsonObject();
            JsonArray matchesArray = jsonResponse.getAsJsonArray("matches");
            
            List<GrepMatch> matches = new ArrayList<>();
            for (int i = 0; i < matchesArray.size(); i++) {
                JsonObject matchObj = matchesArray.get(i).getAsJsonObject();
                String matchPath = matchObj.get("path").getAsString();
                int line = matchObj.get("line").getAsInt();
                String text = matchObj.get("text").getAsString();
                matches.add(new GrepMatch(matchPath, line, text));
            }
            
            return matches;
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    @Override
    public List<FileInfo> globInfo(String pattern, String path) {
        try {
            String url = baseUrl + "/api/glob?pattern=" + encodeParam(pattern) 
                    + "&path=" + encodeParam(path);
            String responseBody = sendGetRequest(url);
            
            JsonObject jsonResponse = JsonParser.parseString(responseBody).getAsJsonObject();
            JsonArray filesArray = jsonResponse.getAsJsonArray("files");
            
            List<FileInfo> fileInfos = new ArrayList<>();
            for (int i = 0; i < filesArray.size(); i++) {
                JsonObject fileObj = filesArray.get(i).getAsJsonObject();
                String filePath = fileObj.get("path").getAsString();
                boolean isDir = fileObj.get("is_dir").getAsBoolean();
                int size = fileObj.has("size") ? fileObj.get("size").getAsInt() : 0;
                String modifiedAt = fileObj.has("modified_at") ? fileObj.get("modified_at").getAsString() : "";
                fileInfos.add(new FileInfo(filePath, isDir, size, modifiedAt));
            }
            
            return fileInfos;
        } catch (Exception e) {
            throw new RuntimeException("Failed to glob pattern: " + pattern, e);
        }
    }

    @Override
    public WriteResult write(String filePath, String content) {
        try {
            String url = baseUrl + "/api/write";
            
            JsonObject requestBody = new JsonObject();
            requestBody.addProperty("file_path", filePath);
            requestBody.addProperty("content", content);
            
            String responseBody = sendPostRequest(url, requestBody.toString());
            
            JsonObject jsonResponse = JsonParser.parseString(responseBody).getAsJsonObject();
            
            if (jsonResponse.has("error") && !jsonResponse.get("error").isJsonNull()) {
                String error = jsonResponse.get("error").getAsString();
                return WriteResult.error(error);
            }
            
            String path = jsonResponse.get("path").getAsString();
            return WriteResult.success(path);
        } catch (Exception e) {
            return WriteResult.error("Error: Failed to write file '" + filePath + "': " + e.getMessage());
        }
    }

    @Override
    public EditResult edit(String filePath, String oldString, String newString, boolean replaceAll) {
        try {
            String url = baseUrl + "/api/edit";
            
            JsonObject requestBody = new JsonObject();
            requestBody.addProperty("file_path", filePath);
            requestBody.addProperty("old_string", oldString);
            requestBody.addProperty("new_string", newString);
            requestBody.addProperty("replace_all", replaceAll);
            
            String responseBody = sendPostRequest(url, requestBody.toString());
            
            JsonObject jsonResponse = JsonParser.parseString(responseBody).getAsJsonObject();
            
            if (jsonResponse.has("error") && !jsonResponse.get("error").isJsonNull()) {
                String error = jsonResponse.get("error").getAsString();
                return EditResult.error(error);
            }
            
            String path = jsonResponse.get("path").getAsString();
            int occurrences = jsonResponse.has("occurrences") ? jsonResponse.get("occurrences").getAsInt() : 0;
            return EditResult.success(path, occurrences);
        } catch (Exception e) {
            return EditResult.error("Error: Failed to edit file '" + filePath + "': " + e.getMessage());
        }
    }
    
    public String getBaseUrl() {
        return baseUrl;
    }
}
