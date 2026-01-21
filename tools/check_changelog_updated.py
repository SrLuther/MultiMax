#!/usr/bin/env python3
"""
Pre-commit hook to ensure CHANGELOG.md is updated when code changes are committed.
Blocks commits if code files are staged but CHANGELOG.md is not.
"""

import subprocess
import sys
from pathlib import Path


def get_staged_files():
    """Get list of staged files from git index."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=False,
        )
        return set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
    except Exception as e:
        print(f"[ERROR] Unable to get staged files: {e}")
        return set()


def is_documentation_only(staged_files):
    """Check if only documentation files are being committed."""
    code_extensions = {".py", ".html", ".js", ".css", ".sql", ".json"}
    doc_only_files = {"README.md", "CHANGELOG.md", ".pre-commit-config.yaml", "pyproject.toml"}

    for file in staged_files:
        if file:  # Skip empty strings
            file_path = Path(file)
            # Check if it's a code file or other substantial file
            if file_path.suffix in code_extensions or file not in doc_only_files:
                if file != "CHANGELOG.md":  # CHANGELOG itself doesn't count as code
                    return False
    return True


def main():
    """Main hook logic."""
    staged_files = get_staged_files()

    if not staged_files or not any(staged_files):
        return 0  # No files staged, allow commit

    # Check if this is documentation-only commit
    if is_documentation_only(staged_files):
        return 0  # Only docs/config changed, allow commit

    # Check if CHANGELOG.md is in staged files
    changelog_updated = "CHANGELOG.md" in staged_files

    if not changelog_updated:
        print("\n" + "=" * 70)
        print("[ERROR] Code modified but CHANGELOG.md was not updated")
        print("=" * 70)
        print("\nModified files (staged):")
        for f in sorted(staged_files):
            if f:
                print(f"   * {f}")
        print("\nPlease:")
        print("   1. Open CHANGELOG.md")
        print("   2. Add entry in [Unreleased] or create new version section")
        print("   3. Run: git add CHANGELOG.md")
        print("   4. Run commit again: git commit")
        print("\nTip: Use semantic versioning (MAJOR.MINOR.PATCH)")
        print("=" * 70 + "\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
