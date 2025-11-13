#!/usr/bin/env python3
"""
Verification script for Docker setup.
Checks that all required files are present and properly configured.
"""

import os
import sys
from pathlib import Path


class DockerSetupVerifier:
    """Verify Docker setup for FileServer."""

    def __init__(self):
        self.fileserver_dir = Path(__file__).parent
        self.checks_passed = 0
        self.checks_failed = 0

    def check_file_exists(self, filename: str, description: str) -> bool:
        """Check if a file exists."""
        filepath = self.fileserver_dir / filename
        if filepath.exists():
            print(f"✅ {description}: {filename}")
            self.checks_passed += 1
            return True
        else:
            print(f"❌ {description}: {filename} - NOT FOUND")
            self.checks_failed += 1
            return False

    def check_file_executable(self, filename: str) -> bool:
        """Check if a file is executable."""
        filepath = self.fileserver_dir / filename
        if filepath.exists() and os.access(filepath, os.X_OK):
            print(f"✅ {filename} is executable")
            self.checks_passed += 1
            return True
        else:
            print(f"⚠️  {filename} is not executable (run: chmod +x {filename})")
            return True  # Not a critical failure

    def check_dockerfile(self) -> bool:
        """Check Dockerfile contents."""
        filepath = self.fileserver_dir / "Dockerfile"
        if not filepath.exists():
            return False

        content = filepath.read_text()
        checks = {
            "FROM python:3.11": "Python 3.11 base image",
            "EXPOSE 8080": "Port 8080 exposed",
            "FILESERVER_MODE": "Mode configuration",
            "HEALTHCHECK": "Health check configured",
            "docker-entrypoint.sh": "Entry point script reference",
        }

        all_ok = True
        for check, desc in checks.items():
            if check in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ Missing: {desc}")
                all_ok = False

        if all_ok:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return all_ok

    def check_docker_compose(self) -> bool:
        """Check docker-compose.yml contents."""
        filepath = self.fileserver_dir / "docker-compose.yml"
        if not filepath.exists():
            return False

        content = filepath.read_text()
        checks = {
            "fileserver-fastapi": "FastAPI service defined",
            "fileserver-standard": "Standard service defined",
            "fileserver-data": "Data volume defined",
            "8080:8080": "Port mapping configured",
            "FILESERVER_MODE": "Mode environment variable",
            "healthcheck": "Health check configured",
        }

        all_ok = True
        for check, desc in checks.items():
            if check in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ Missing: {desc}")
                all_ok = False

        if all_ok:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return all_ok

    def check_entrypoint_script(self) -> bool:
        """Check docker-entrypoint.sh contents."""
        filepath = self.fileserver_dir / "docker-entrypoint.sh"
        if not filepath.exists():
            return False

        content = filepath.read_text()
        checks = {
            "#!/bin/bash": "Bash shebang",
            "FILESERVER_ROOT_DIR": "Root directory variable",
            "FILESERVER_MODE": "Mode variable",
            "fastapi": "FastAPI mode support",
            "standard": "Standard mode support",
            "python -m fileserver": "Server launch command",
        }

        all_ok = True
        for check, desc in checks.items():
            if check in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ Missing: {desc}")
                all_ok = False

        if all_ok:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return all_ok

    def check_dockerignore(self) -> bool:
        """Check .dockerignore contents."""
        filepath = self.fileserver_dir / ".dockerignore"
        if not filepath.exists():
            return False

        content = filepath.read_text()
        checks = {
            "__pycache__": "Python cache exclusion",
            ".venv": "Virtual environment exclusion",
            "*.pyc": "Python bytecode exclusion",
            ".git": "Git directory exclusion",
        }

        all_ok = True
        for check, desc in checks.items():
            if check in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ Missing: {desc}")
                all_ok = False

        if all_ok:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return all_ok

    def check_documentation(self) -> bool:
        """Check if documentation is comprehensive."""
        filepath = self.fileserver_dir / "DOCKER.md"
        if not filepath.exists():
            return False

        content = filepath.read_text()
        size_kb = len(content) / 1024

        checks = {
            "Quick Start": "Quick start section",
            "Configuration": "Configuration section",
            "Environment Variables": "Environment variables documented",
            "docker-compose": "Docker Compose examples",
            "docker build": "Docker build examples",
            "Production": "Production deployment section",
            "Health": "Health check documentation",
            "Troubleshooting": "Troubleshooting section",
        }

        all_ok = True
        for check, desc in checks.items():
            if check in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ Missing: {desc}")
                all_ok = False

        print(f"  ℹ  Documentation size: {size_kb:.1f} KB")

        if all_ok:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return all_ok

    def check_readme_updated(self) -> bool:
        """Check if README was updated with Docker info."""
        filepath = self.fileserver_dir / "README.md"
        if not filepath.exists():
            return False

        content = filepath.read_text()
        checks = {
            "Docker": "Docker mentioned",
            "docker-compose": "Docker Compose examples",
            "DOCKER.md": "Reference to Docker documentation",
        }

        all_ok = True
        for check, desc in checks.items():
            if check in content:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ Missing: {desc}")
                all_ok = False

        if all_ok:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return all_ok

    def run_verification(self) -> bool:
        """Run all verification checks."""
        print("=" * 80)
        print("Docker Setup Verification for DeepAgents FileServer")
        print("=" * 80)
        print()

        # Core Docker files
        print("📦 Core Docker Files:")
        self.check_file_exists("Dockerfile", "Dockerfile")
        self.check_file_exists("docker-compose.yml", "Docker Compose file")
        self.check_file_exists("docker-entrypoint.sh", "Entry point script")
        self.check_file_exists(".dockerignore", "Docker ignore file")
        print()

        # Executable permissions
        print("🔧 File Permissions:")
        self.check_file_executable("docker-entrypoint.sh")
        print()

        # Documentation
        print("📚 Documentation:")
        self.check_file_exists("DOCKER.md", "Docker documentation")
        self.check_file_exists("DOCKER_IMPLEMENTATION.md", "Implementation details")
        print()

        # Test scripts
        print("🧪 Test Scripts:")
        self.check_file_exists("test_docker.py", "Python test script")
        self.check_file_exists("manual_docker_test.sh", "Bash test script")
        print()

        # Content validation
        print("📋 Dockerfile Configuration:")
        self.check_dockerfile()
        print()

        print("📋 Docker Compose Configuration:")
        self.check_docker_compose()
        print()

        print("📋 Entry Point Script:")
        self.check_entrypoint_script()
        print()

        print("📋 Docker Ignore:")
        self.check_dockerignore()
        print()

        print("📋 Docker Documentation:")
        self.check_documentation()
        print()

        print("📋 README Updates:")
        self.check_readme_updated()
        print()

        # Summary
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"✅ Passed: {self.checks_passed}")
        print(f"❌ Failed: {self.checks_failed}")
        print(f"Total:  {self.checks_passed + self.checks_failed}")
        print()

        if self.checks_failed == 0:
            print("🎉 All checks passed! Docker setup is complete and ready to use.")
            print()
            print("Next steps:")
            print("  1. Build the image:     docker build -t deepagents-fileserver .")
            print("  2. Or use compose:      docker-compose up -d fileserver-fastapi")
            print("  3. View documentation:  cat DOCKER.md")
            print("  4. Run tests:           python3 test_docker.py")
            print()
            return True
        else:
            print("⚠️  Some checks failed. Please review the issues above.")
            print()
            return False


def main():
    """Main verification function."""
    verifier = DockerSetupVerifier()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
