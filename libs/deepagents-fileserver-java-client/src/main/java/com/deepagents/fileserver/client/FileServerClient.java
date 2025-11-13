package com.deepagents.fileserver.client;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Java client for DeepAgents FileServer API.
 * Supports all BackendProtocol operations exposed via HTTP endpoints.
 */
public class FileServerClient implements AutoCloseable {
    private final String baseUrl;
    private final String apiKey;
    private final Gson gson;
    private final int connectTimeout;
    private final int readTimeout;

    /**
     * Create a new FileServerClient.
     *
     * @param baseUrl Base URL of the file server (e.g., "http://localhost:8080")
     */
    public FileServerClient(String baseUrl) {
        this(baseUrl, null, 5000, 30000);
    }

    /**
     * Create a new FileServerClient with API key authentication.
     *
     * @param baseUrl Base URL of the file server (e.g., "http://localhost:8080")
     * @param apiKey  API key for authentication (null if not required)
     */
    public FileServerClient(String baseUrl, String apiKey) {
        this(baseUrl, apiKey, 5000, 30000);
    }

    /**
     * Create a new FileServerClient with custom timeouts.
     *
     * @param baseUrl        Base URL of the file server (e.g., "http://localhost:8080")
     * @param apiKey         API key for authentication (null if not required)
     * @param connectTimeout Connection timeout in milliseconds
     * @param readTimeout    Read timeout in milliseconds
     */
    public FileServerClient(String baseUrl, String apiKey, int connectTimeout, int readTimeout) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.apiKey = apiKey;
        this.connectTimeout = connectTimeout;
        this.readTimeout = readTimeout;
        this.gson = new GsonBuilder()
                .setFieldNamingStrategy(f -> {
                    String name = f.getName();
                    if (name.equals("filePath")) return "file_path";
                    if (name.equals("oldString")) return "old_string";
                    if (name.equals("newString")) return "new_string";
                    if (name.equals("replaceAll")) return "replace_all";
                    if (name.equals("isDir")) return "is_dir";
                    if (name.equals("modifiedAt")) return "modified_at";
                    return toSnakeCase(name);
                })
                .create();
    }

    private String toSnakeCase(String camelCase) {
        return camelCase.replaceAll("([a-z])([A-Z])", "$1_$2").toLowerCase();
    }

    /**
     * Health check endpoint.
     *
     * @return true if server is healthy
     * @throws IOException if request fails
     */
    public boolean healthCheck() throws IOException {
        String response = sendGetRequest("/health", null);
        JsonObject json = JsonParser.parseString(response).getAsJsonObject();
        return "ok".equals(json.get("status").getAsString());
    }

    /**
     * List files and directories in the specified path.
     *
     * @param path Directory path to list (null for current directory)
     * @return List of FileInfo objects
     * @throws IOException if request fails
     */
    public List<FileInfo> listDirectory(String path) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (path != null && !path.isEmpty()) {
            params.put("path", path);
        }
        String response = sendGetRequest("/api/ls", params);
        JsonObject json = JsonParser.parseString(response).getAsJsonObject();
        return gson.fromJson(json.get("files"), new TypeToken<List<FileInfo>>() {
        }.getType());
    }

    /**
     * Read file content with line numbers.
     *
     * @param filePath Path to the file to read
     * @return Formatted file content with line numbers
     * @throws IOException if request fails
     */
    public String readFile(String filePath) throws IOException {
        return readFile(filePath, 0, 2000);
    }

    /**
     * Read file content with line numbers and pagination.
     *
     * @param filePath Path to the file to read
     * @param offset   Line offset to start reading from
     * @param limit    Maximum number of lines to read
     * @return Formatted file content with line numbers
     * @throws IOException if request fails
     */
    public String readFile(String filePath, int offset, int limit) throws IOException {
        Map<String, String> params = new HashMap<>();
        params.put("file_path", filePath);
        params.put("offset", String.valueOf(offset));
        params.put("limit", String.valueOf(limit));
        String response = sendGetRequest("/api/read", params);
        JsonObject json = JsonParser.parseString(response).getAsJsonObject();
        return json.get("content").getAsString();
    }

    /**
     * Create a new file with the specified content.
     *
     * @param filePath Path where the file should be created
     * @param content  Content to write to the file
     * @return WriteResponse with error or path
     * @throws IOException if request fails
     */
    public WriteResponse writeFile(String filePath, String content) throws IOException {
        WriteRequest request = new WriteRequest(filePath, content);
        String response = sendPostRequest("/api/write", gson.toJson(request));
        return gson.fromJson(response, WriteResponse.class);
    }

    /**
     * Edit a file by replacing string occurrences.
     *
     * @param filePath   Path to the file to edit
     * @param oldString  String to replace
     * @param newString  Replacement string
     * @param replaceAll If true, replace all occurrences; otherwise replace only first
     * @return EditResponse with error, path, and number of occurrences replaced
     * @throws IOException if request fails
     */
    public EditResponse editFile(String filePath, String oldString, String newString, boolean replaceAll) throws IOException {
        EditRequest request = new EditRequest(filePath, oldString, newString, replaceAll);
        String response = sendPostRequest("/api/edit", gson.toJson(request));
        return gson.fromJson(response, EditResponse.class);
    }

    /**
     * Edit a file by replacing the first occurrence of a string.
     *
     * @param filePath  Path to the file to edit
     * @param oldString String to replace
     * @param newString Replacement string
     * @return EditResponse with error, path, and number of occurrences replaced
     * @throws IOException if request fails
     */
    public EditResponse editFile(String filePath, String oldString, String newString) throws IOException {
        return editFile(filePath, oldString, newString, false);
    }

    /**
     * Search for patterns in files using regular expressions.
     *
     * @param pattern Regular expression pattern to search for
     * @return List of GrepMatch objects
     * @throws IOException if request fails
     */
    public List<GrepMatch> grep(String pattern) throws IOException {
        return grep(pattern, null, null);
    }

    /**
     * Search for patterns in files using regular expressions.
     *
     * @param pattern Regular expression pattern to search for
     * @param path    Base path to search in (null for current directory)
     * @param glob    Glob pattern to filter files (e.g., "*.py")
     * @return List of GrepMatch objects
     * @throws IOException if request fails
     */
    public List<GrepMatch> grep(String pattern, String path, String glob) throws IOException {
        Map<String, String> params = new HashMap<>();
        params.put("pattern", pattern);
        if (path != null && !path.isEmpty()) {
            params.put("path", path);
        }
        if (glob != null && !glob.isEmpty()) {
            params.put("glob", glob);
        }
        String response = sendGetRequest("/api/grep", params);
        JsonObject json = JsonParser.parseString(response).getAsJsonObject();
        return gson.fromJson(json.get("matches"), new TypeToken<List<GrepMatch>>() {
        }.getType());
    }

    /**
     * Find files matching a glob pattern.
     *
     * @param pattern Glob pattern (e.g., "*.txt", "**\/*.py")
     * @return List of FileInfo objects for matching files
     * @throws IOException if request fails
     */
    public List<FileInfo> glob(String pattern) throws IOException {
        return glob(pattern, "/");
    }

    /**
     * Find files matching a glob pattern.
     *
     * @param pattern Glob pattern (e.g., "*.txt", "**\/*.py")
     * @param path    Base path to search from
     * @return List of FileInfo objects for matching files
     * @throws IOException if request fails
     */
    public List<FileInfo> glob(String pattern, String path) throws IOException {
        Map<String, String> params = new HashMap<>();
        params.put("pattern", pattern);
        if (path != null && !path.isEmpty()) {
            params.put("path", path);
        }
        String response = sendGetRequest("/api/glob", params);
        JsonObject json = JsonParser.parseString(response).getAsJsonObject();
        return gson.fromJson(json.get("files"), new TypeToken<List<FileInfo>>() {
        }.getType());
    }

    private String sendGetRequest(String endpoint, Map<String, String> params) throws IOException {
        StringBuilder urlBuilder = new StringBuilder(baseUrl).append(endpoint);
        if (params != null && !params.isEmpty()) {
            urlBuilder.append("?");
            boolean first = true;
            for (Map.Entry<String, String> entry : params.entrySet()) {
                if (!first) {
                    urlBuilder.append("&");
                }
                urlBuilder.append(URLEncoder.encode(entry.getKey(), StandardCharsets.UTF_8))
                        .append("=")
                        .append(URLEncoder.encode(entry.getValue(), StandardCharsets.UTF_8));
                first = false;
            }
        }

        URL url = new URL(urlBuilder.toString());
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(connectTimeout);
        conn.setReadTimeout(readTimeout);

        if (apiKey != null && !apiKey.isEmpty()) {
            conn.setRequestProperty("X-API-Key", apiKey);
        }

        int responseCode = conn.getResponseCode();
        if (responseCode >= 400) {
            throw new IOException("HTTP Error " + responseCode + ": " + readErrorStream(conn));
        }

        return readInputStream(conn.getInputStream());
    }

    private String sendPostRequest(String endpoint, String jsonBody) throws IOException {
        URL url = new URL(baseUrl + endpoint);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setConnectTimeout(connectTimeout);
        conn.setReadTimeout(readTimeout);
        conn.setDoOutput(true);

        if (apiKey != null && !apiKey.isEmpty()) {
            conn.setRequestProperty("X-API-Key", apiKey);
        }

        try (OutputStream os = conn.getOutputStream()) {
            byte[] input = jsonBody.getBytes(StandardCharsets.UTF_8);
            os.write(input, 0, input.length);
        }

        int responseCode = conn.getResponseCode();
        if (responseCode >= 400) {
            throw new IOException("HTTP Error " + responseCode + ": " + readErrorStream(conn));
        }

        return readInputStream(conn.getInputStream());
    }

    private String readInputStream(InputStream inputStream) throws IOException {
        byte[] buffer = new byte[8192];
        StringBuilder response = new StringBuilder();
        int bytesRead;
        while ((bytesRead = inputStream.read(buffer)) != -1) {
            response.append(new String(buffer, 0, bytesRead, StandardCharsets.UTF_8));
        }
        return response.toString();
    }

    private String readErrorStream(HttpURLConnection conn) throws IOException {
        InputStream errorStream = conn.getErrorStream();
        if (errorStream != null) {
            return readInputStream(errorStream);
        }
        return conn.getResponseMessage();
    }

    @Override
    public void close() {
        // No resources to close
    }
}
