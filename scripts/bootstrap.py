#!/usr/bin/env python3
"""Bootstrap script for environment verification and directory synchronization.

Validates developer system requirements, validates dependencies, ensures log
paths exist, and prepares local database pools.
"""

import os
import sys

# Define base relative directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def check_python_version() -> bool:
    """Verifies that the execution environment is running compatible Python."""
    required_major = 3
    required_minor = 10

    current = sys.version_info
    if current.major < required_major or (
        current.major == required_major and current.minor < required_minor
    ):
        print(
            f"[-] ERROR: Python version {required_major}.{required_minor}+ is required. "
            f"Detected: {current.major}.{current.minor}.{current.micro}",
            file=sys.stderr,
        )
        return False
    print(f"[+] Python version: {current.major}.{current.minor}.{current.micro} (Pass)")
    return True


def verify_directories() -> bool:
    """Creates essential runtime directories if missing."""
    directories = ["data", "logs", "models", "reports/benchmarks", "reports/figures"]
    success = True
    for folder in directories:
        path = os.path.join(BASE_DIR, folder)
        try:
            os.makedirs(path, exist_ok=True)
            print(f"[+] Directory checked/created: {folder}/")
        except Exception as e:
            print(f"[-] ERROR: Failed to create {folder}/. Error: {e}", file=sys.stderr)
            success = False
    return success


def check_core_imports() -> bool:
    """Sanity checks that critical dependencies can be imported successfully."""
    dependencies = [
        "pandas",
        "numpy",
        "pydantic",
        "pydantic_settings",
        "yaml",
        "xgboost",
        "pytest",
    ]
    success = True
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"[+] Dependency import verified: {dep}")
        except ImportError:
            print(
                f"[-] ERROR: Failed to import dependency: {dep}. Check requirements.txt.",
                file=sys.stderr,
            )
            success = False
    return success


def verify_configuration() -> bool:
    """Validates configuration setup and validates loader models."""
    try:
        from src.config.config_loader import settings

        print(
            f"[+] Configuration loading validation: Environment is '{settings.env}' (Pass)"
        )
        return True
    except Exception as e:
        print(
            f"[-] ERROR: Configuration validation failed. Error: {e}", file=sys.stderr
        )
        return False


def main() -> None:
    print("=" * 60)
    print("Google Search Quality Platform: Bootstrapping Environment...")
    print("=" * 60)

    steps = [
        check_python_version(),
        verify_directories(),
        check_core_imports(),
        verify_configuration(),
    ]

    print("=" * 60)
    if all(steps):
        print("[+] BOOTSTRAP SUCCESSFUL: Environment is ready for execution.")
        sys.exit(0)
    else:
        print(
            "[-] BOOTSTRAP FAILED: Please fix errors detailed above.", file=sys.stderr
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
