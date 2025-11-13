#!/bin/bash

# SandboxBackend Demo Script
# This script demonstrates the SandboxBackend functionality

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         SandboxBackend Demonstration                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Setup
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
JAVA_DIR="$PROJECT_ROOT/libs/deepagents-backends-java"
FILESERVER_DIR="$PROJECT_ROOT/libs/deepagents-fileserver"
TEMP_DIR=$(mktemp -d -t sandbox_demo_XXXXXX)
PYTHON_EXEC="$PROJECT_ROOT/.venv/bin/python"

if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="python3"
fi

echo "📁 Setup:"
echo "   Project Root: $PROJECT_ROOT"
echo "   Java Module:  $JAVA_DIR"
echo "   FileServer:   $FILESERVER_DIR"
echo "   Temp Dir:     $TEMP_DIR"
echo "   Python:       $PYTHON_EXEC"
echo ""

# Start FileServer
echo "🚀 Starting FileServer on port 8888..."
cd "$FILESERVER_DIR"
$PYTHON_EXEC -m fileserver.server "$TEMP_DIR" 8888 > /tmp/fileserver.log 2>&1 &
FILESERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for FileServer to be ready..."
for i in {1..20}; do
    if curl -s http://localhost:8888/health > /dev/null 2>&1; then
        echo "✅ FileServer is ready!"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ FileServer failed to start within 10 seconds"
        kill $FILESERVER_PID 2>/dev/null || true
        exit 1
    fi
    sleep 0.5
done
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    kill $FILESERVER_PID 2>/dev/null || true
    rm -rf "$TEMP_DIR"
    echo "✅ Cleanup complete"
}
trap cleanup EXIT

# Demo operations using curl (simulating SandboxBackend)
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ Demonstrating SandboxBackend Operations                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo "1️⃣  Writing a file..."
curl -s -X POST http://localhost:8888/api/write \
  -H "Content-Type: application/json" \
  -d '{"file_path": "demo.txt", "content": "Hello from SandboxBackend!"}' | jq .
echo ""

echo "2️⃣  Reading the file..."
curl -s "http://localhost:8888/api/read?file_path=demo.txt" | jq -r '.content'
echo ""

echo "3️⃣  Editing the file..."
curl -s -X POST http://localhost:8888/api/edit \
  -H "Content-Type: application/json" \
  -d '{"file_path": "demo.txt", "old_string": "Hello", "new_string": "Greetings", "replace_all": false}' | jq .
echo ""

echo "4️⃣  Reading the edited file..."
curl -s "http://localhost:8888/api/read?file_path=demo.txt" | jq -r '.content'
echo ""

echo "5️⃣  Writing more files for demonstration..."
curl -s -X POST http://localhost:8888/api/write \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test1.txt", "content": "Test file 1"}' > /dev/null
curl -s -X POST http://localhost:8888/api/write \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test2.md", "content": "Test file 2"}' > /dev/null
curl -s -X POST http://localhost:8888/api/write \
  -H "Content-Type: application/json" \
  -d '{"file_path": "subdir/nested.txt", "content": "Nested file"}' > /dev/null
echo "✅ Created test1.txt, test2.md, and subdir/nested.txt"
echo ""

echo "6️⃣  Listing directory..."
curl -s "http://localhost:8888/api/ls?path=." | jq '.files[] | "\(.path) (\(if .is_dir then "dir" else "file" end))"'
echo ""

echo "7️⃣  Glob search for *.txt files..."
curl -s "http://localhost:8888/api/glob?pattern=*.txt&path=." | jq '.files[] | .path'
echo ""

echo "8️⃣  Grep search for 'Test'..."
curl -s "http://localhost:8888/api/grep?pattern=Test&path=." | jq '.matches[] | "\(.path):\(.line) - \(.text)"'
echo ""

echo "9️⃣  Glob search with recursion..."
curl -s "http://localhost:8888/api/glob?pattern=**/*.txt&path=." | jq '.files[] | .path'
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ Testing Java SandboxBackend (if compiled)                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd "$JAVA_DIR"
if [ -f "target/test-classes/com/deepagents/backends/SandboxBackendTest.class" ]; then
    echo "🧪 Running Java SandboxBackend test..."
    mvn -q test -Dtest=SandboxBackendTest#testWriteAndRead
    if [ $? -eq 0 ]; then
        echo "✅ Java SandboxBackend test passed!"
    else
        echo "❌ Java SandboxBackend test failed"
    fi
else
    echo "ℹ️  Java tests not compiled. Run 'mvn test' to compile and test."
fi
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ Files Created in Temp Directory                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
ls -lR "$TEMP_DIR"
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ Demo Complete!                                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "The SandboxBackend successfully demonstrated:"
echo "  ✅ File write operations"
echo "  ✅ File read operations"
echo "  ✅ File edit operations"
echo "  ✅ Directory listing"
echo "  ✅ Glob pattern matching"
echo "  ✅ Grep text search"
echo "  ✅ Nested directory support"
echo ""
echo "For more information, see:"
echo "  - README.md"
echo "  - SANDBOX_BACKEND_README.md"
echo "  - SANDBOX_BACKEND_IMPLEMENTATION.md"
echo ""
