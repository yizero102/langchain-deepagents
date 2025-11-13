#!/usr/bin/env python3
"""
Test script to verify Docker deployment of FileServer.
Tests both standard and FastAPI server modes.
"""

import os
import sys
import time
import json
import subprocess
import requests
from typing import Optional


class DockerTester:
    """Test Docker deployment of FileServer."""

    def __init__(self, mode: str = "fastapi", port: int = 8080):
        self.mode = mode
        self.port = port
        self.container_name = f"test-fileserver-{mode}"
        self.base_url = f"http://localhost:{port}"
        self.api_key: Optional[str] = None

    def cleanup_existing_containers(self):
        """Remove any existing test containers."""
        print(f"🧹 Cleaning up existing containers...")
        subprocess.run(["docker", "rm", "-f", self.container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def build_image(self) -> bool:
        """Build the Docker image."""
        print("🔨 Building Docker image...")
        fileserver_dir = os.path.dirname(os.path.abspath(__file__))
        result = subprocess.run(["docker", "build", "-t", "deepagents-fileserver", "."], cwd=fileserver_dir)
        return result.returncode == 0

    def start_container(self) -> bool:
        """Start the Docker container."""
        print(f"🚀 Starting {self.mode} server in Docker...")

        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            self.container_name,
            "-p",
            f"{self.port}:8080",
            "-e",
            f"FILESERVER_MODE={self.mode}",
        ]

        # For FastAPI mode, set a known API key
        if self.mode == "fastapi":
            self.api_key = "test-api-key-12345"
            cmd.extend(["-e", f"FILESERVER_API_KEY={self.api_key}"])

        cmd.append("deepagents-fileserver")

        result = subprocess.run(cmd)

        if result.returncode != 0:
            return False

        # Wait for container to start
        print("⏳ Waiting for container to start...")
        time.sleep(5)

        return True

    def wait_for_health(self, timeout: int = 30) -> bool:
        """Wait for the server to become healthy."""
        print("🏥 Checking server health...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Server is healthy!")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)

        print("❌ Server health check timeout")
        return False

    def get_headers(self) -> dict:
        """Get request headers (including API key if needed)."""
        headers = {"Content-Type": "application/json"}
        if self.mode == "fastapi" and self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def test_list_directory(self) -> bool:
        """Test listing directory."""
        print("\n📂 Testing list directory...")
        try:
            response = requests.get(f"{self.base_url}/api/ls", params={"path": "/"}, headers=self.get_headers())

            if response.status_code == 200:
                data = response.json()
                print(f"✅ List directory successful: {len(data.get('files', []))} files")
                return True
            else:
                print(f"❌ List directory failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ List directory error: {e}")
            return False

    def test_write_file(self) -> bool:
        """Test writing a file."""
        print("\n📝 Testing write file...")
        try:
            response = requests.post(
                f"{self.base_url}/api/write", headers=self.get_headers(), json={"file_path": "/test_docker.txt", "content": "Hello from Docker test!"}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("error") is None:
                    print("✅ Write file successful")
                    return True
                else:
                    print(f"❌ Write file error: {data.get('error')}")
                    return False
            else:
                print(f"❌ Write file failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Write file error: {e}")
            return False

    def test_read_file(self) -> bool:
        """Test reading a file."""
        print("\n📖 Testing read file...")
        try:
            response = requests.get(f"{self.base_url}/api/read", params={"file_path": "/test_docker.txt"}, headers=self.get_headers())

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                if "Hello from Docker test!" in content:
                    print("✅ Read file successful")
                    return True
                else:
                    print(f"❌ Read file unexpected content: {content}")
                    return False
            else:
                print(f"❌ Read file failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Read file error: {e}")
            return False

    def test_edit_file(self) -> bool:
        """Test editing a file."""
        print("\n✏️  Testing edit file...")
        try:
            response = requests.post(
                f"{self.base_url}/api/edit",
                headers=self.get_headers(),
                json={"file_path": "/test_docker.txt", "old_string": "Docker", "new_string": "Container"},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("error") is None and data.get("occurrences", 0) > 0:
                    print("✅ Edit file successful")
                    return True
                else:
                    print(f"❌ Edit file error: {data}")
                    return False
            else:
                print(f"❌ Edit file failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Edit file error: {e}")
            return False

    def test_grep(self) -> bool:
        """Test grep search."""
        print("\n🔍 Testing grep...")
        try:
            response = requests.get(f"{self.base_url}/api/grep", params={"pattern": "Container", "path": "/"}, headers=self.get_headers())

            if response.status_code == 200:
                data = response.json()
                matches = data.get("matches", [])
                if len(matches) > 0:
                    print(f"✅ Grep successful: {len(matches)} matches")
                    return True
                else:
                    print("❌ Grep found no matches")
                    return False
            else:
                print(f"❌ Grep failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Grep error: {e}")
            return False

    def test_glob(self) -> bool:
        """Test glob pattern matching."""
        print("\n🌐 Testing glob...")
        try:
            response = requests.get(f"{self.base_url}/api/glob", params={"pattern": "*.txt", "path": "/"}, headers=self.get_headers())

            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                if len(files) > 0:
                    print(f"✅ Glob successful: {len(files)} files")
                    return True
                else:
                    print("❌ Glob found no files")
                    return False
            else:
                print(f"❌ Glob failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Glob error: {e}")
            return False

    def test_api_docs(self) -> bool:
        """Test API documentation (FastAPI only)."""
        if self.mode != "fastapi":
            return True

        print("\n📚 Testing API documentation...")
        try:
            response = requests.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                print("✅ API docs accessible")
                return True
            else:
                print(f"❌ API docs failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API docs error: {e}")
            return False

    def show_logs(self):
        """Show container logs."""
        print("\n📋 Container logs:")
        print("=" * 80)
        subprocess.run(["docker", "logs", self.container_name])
        print("=" * 80)

    def cleanup(self):
        """Clean up test container."""
        print(f"\n🧹 Cleaning up...")
        subprocess.run(["docker", "rm", "-f", self.container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def run_tests(self) -> bool:
        """Run all tests."""
        print(f"\n{'=' * 80}")
        print(f"🐳 Testing FileServer Docker Deployment ({self.mode.upper()} mode)")
        print(f"{'=' * 80}")

        try:
            # Setup
            self.cleanup_existing_containers()

            if not self.build_image():
                print("❌ Failed to build Docker image")
                return False

            if not self.start_container():
                print("❌ Failed to start container")
                return False

            if not self.wait_for_health():
                self.show_logs()
                return False

            # Run tests
            tests = [
                self.test_list_directory,
                self.test_write_file,
                self.test_read_file,
                self.test_edit_file,
                self.test_grep,
                self.test_glob,
                self.test_api_docs,
            ]

            passed = 0
            failed = 0

            for test in tests:
                if test():
                    passed += 1
                else:
                    failed += 1

            # Summary
            print(f"\n{'=' * 80}")
            print(f"📊 Test Results ({self.mode.upper()} mode)")
            print(f"{'=' * 80}")
            print(f"✅ Passed: {passed}")
            print(f"❌ Failed: {failed}")
            print(f"Total: {passed + failed}")

            if failed == 0:
                print(f"\n🎉 All tests passed for {self.mode.upper()} mode!")
                return True
            else:
                print(f"\n⚠️  Some tests failed for {self.mode.upper()} mode")
                self.show_logs()
                return False

        finally:
            self.cleanup()


def main():
    """Main test function."""
    modes = ["fastapi", "standard"]
    all_passed = True

    for mode in modes:
        tester = DockerTester(mode=mode, port=8080)
        if not tester.run_tests():
            all_passed = False
        time.sleep(2)  # Brief pause between tests

    # Final summary
    print(f"\n{'=' * 80}")
    print("🏁 Final Summary")
    print(f"{'=' * 80}")

    if all_passed:
        print("✅ All Docker tests passed successfully!")
        print("\n🐳 Docker deployment is ready for production!")
        print("\nQuick start commands:")
        print("  docker-compose up -d fileserver-fastapi")
        print("  docker logs -f deepagents-fileserver-fastapi")
        sys.exit(0)
    else:
        print("❌ Some Docker tests failed")
        print("\nPlease review the logs above and fix the issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()
