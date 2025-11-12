#!/bin/bash
# Manual test script for FileServer
# This script demonstrates how to use curl to interact with the FileServer

set -e

BASE_URL="http://localhost:8080"
echo "FileServer Manual Test Script"
echo "=============================="
echo "Make sure the FileServer is running at $BASE_URL"
echo ""

# Health check
echo "1. Health Check"
echo "---------------"
curl -s "$BASE_URL/health" | jq '.'
echo ""

# Write a file
echo "2. Write a new file"
echo "-------------------"
curl -s -X POST "$BASE_URL/api/write" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test_manual.txt", "content": "Hello from manual test!\nLine 2\nLine 3"}' | jq '.'
echo ""

# Read the file
echo "3. Read the file"
echo "----------------"
curl -s "$BASE_URL/api/read?file_path=test_manual.txt" | jq -r '.content'
echo ""

# Edit the file
echo "4. Edit the file"
echo "----------------"
curl -s -X POST "$BASE_URL/api/edit" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test_manual.txt", "old_string": "manual test", "new_string": "FileServer"}' | jq '.'
echo ""

# Read after edit
echo "5. Read after edit"
echo "------------------"
curl -s "$BASE_URL/api/read?file_path=test_manual.txt" | jq -r '.content'
echo ""

# List directory
echo "6. List directory"
echo "-----------------"
curl -s "$BASE_URL/api/ls?path=." | jq '.files[] | {path: .path, is_dir: .is_dir, size: .size}' | head -20
echo ""

# Grep search
echo "7. Search for pattern"
echo "---------------------"
curl -s "$BASE_URL/api/grep?pattern=FileServer&path=." | jq '.matches[] | {path: .path, line: .line, text: .text}'
echo ""

# Glob pattern
echo "8. Glob pattern matching"
echo "------------------------"
curl -s "$BASE_URL/api/glob?pattern=*.txt&path=." | jq '.files[] | {path: .path, size: .size}'
echo ""

echo "=============================="
echo "All manual tests completed!"
echo "=============================="
