#!/usr/bin/env python3
"""
Pre-commit hook to ensure CHANGELOG.md is properly updated when code changes are committed.

Rules:
1. Blocks commits if code files are staged but CHANGELOG.md is not updated
2. REQUIRES creation of NEW version (never edit existing versions)
3. Prevents modification of already-released versions
4. Allows only appending new versions at the top
"""

import re
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


def get_changelog_diff():
    """Get the diff of CHANGELOG.md to see what was added/removed."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "CHANGELOG.md"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
    except Exception as e:
        print(f"[ERROR] Unable to get CHANGELOG diff: {e}")
        return ""


def get_original_changelog_versions():
    """Get versions from the previous commit (before staging)."""
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:CHANGELOG.md"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode == 0:
            # Find all version headers like ## [1.2.3] or ## [Unreleased]
            versions = re.findall(r"^## \[([^\]]+)\]", result.stdout, re.MULTILINE)
            return set(versions)
        # If HEAD doesn't exist (first commit), return empty set
        return set()
    except Exception:
        return set()


def get_staged_changelog_versions():
    """Get versions from the staged CHANGELOG.md."""
    try:
        result = subprocess.run(
            ["git", "show", ":CHANGELOG.md"],  # Show staged version
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode == 0:
            versions = re.findall(r"^## \[([^\]]+)\]", result.stdout, re.MULTILINE)
            return set(versions)
        return set()
    except Exception:
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


def check_version_format(versions, allow_legacy=True):
    """Validate version format (semantic versioning or [Unreleased]).

    Args:
        versions: Set of version strings to check
        allow_legacy: If True, allows old non-semver formats like 2.0, 2.3 (for backward compat)
    """
    semver_pattern = r"^\d+\.\d+\.\d+$"
    legacy_pattern = r"^\d+\.\d+$"  # Allow legacy 2.0 format

    for version in versions:
        if version == "Unreleased":
            continue
        # Check strict semver
        if re.match(semver_pattern, version):
            continue
        # Check if legacy format is allowed
        if allow_legacy and re.match(legacy_pattern, version):
            continue
        # Neither semver nor legacy - invalid
        return False, version
    return True, None


def main():
    """Main hook logic."""
    staged_files = get_staged_files()

    if not staged_files or not any(staged_files):
        return 0  # No files staged, allow commit

    # Check if this is documentation-only commit
    if is_documentation_only(staged_files):
        return 0  # Only docs/config changed, allow commit

    # Check if CHANGELOG.md is in staged files
    if "CHANGELOG.md" not in staged_files:
        print("\n" + "=" * 80)
        print("[ERROR] Code modified but CHANGELOG.md was not updated")
        print("=" * 80)
        print("\nModified files (staged):")
        for f in sorted(staged_files):
            if f:
                print(f"   * {f}")
        print("\nPlease:")
        print("   1. Open CHANGELOG.md")
        print("   2. ADD NEW VERSION at the top (never edit existing versions)")
        print("   3. Follow format: ## [X.Y.Z] - YYYY-MM-DD")
        print("   4. Run: git add CHANGELOG.md")
        print("   5. Run commit again: git commit")
        print("\nTip: Use semantic versioning (MAJOR.MINOR.PATCH)")
        print("=" * 80 + "\n")
        return 1

    # ===== CHANGELOG is staged, now validate it =====

    original_versions = get_original_changelog_versions()
    staged_versions = get_staged_changelog_versions()

    # Check 1: Version format validation
    valid_format, bad_version = check_version_format(staged_versions)
    if not valid_format:
        print("\n" + "=" * 80)
        print("[ERROR] Invalid version format in CHANGELOG.md")
        print("=" * 80)
        print(f"\nVersion '{bad_version}' does not match semantic versioning (X.Y.Z)")
        print("Valid formats: MAJOR.MINOR.PATCH (e.g., 2.7.4) or 'Unreleased'")
        print("=" * 80 + "\n")
        return 1

    # Check 2: Prevent modification of existing versions
    # A version should only be removed if it's being replaced by a new one
    # NOTE: We only check for "removed" versions that have proper semver format
    # (old badly-formatted versions like 2.0, 2.2 won't affect this check)
    removed_versions = original_versions - staged_versions
    # Filter to only care about properly formatted versions
    semver_pattern = r"^\d+\.\d+\.\d+$"
    removed_releases = {v for v in removed_versions if re.match(semver_pattern, v) or v == "Unreleased"}

    if removed_releases and removed_releases != {"Unreleased"}:
        print("\n" + "=" * 80)
        print("[ERROR] Cannot remove or modify existing RELEASED versions!")
        print("=" * 80)
        print(f"\nRemoved/Modified versions: {', '.join(sorted(removed_releases))}")
        print("\nRules:")
        print("  Create NEW versions at the top")
        print("  Only [Unreleased] can be replaced/removed")
        print("  Never edit released versions (e.g., 2.7.3, 2.7.2, etc.)")
        print("\nHowever, if you meant to CREATE a new version from [Unreleased]:")
        print("  1. Keep [Unreleased] at the top")
        print("  2. Add your new version BELOW it")
        print("  3. Move [Unreleased] content to the new version")
        print("=" * 80 + "\n")
        return 1

    # Check 3: Ensure at least ONE new version was added
    new_versions = staged_versions - original_versions
    if not new_versions:
        print("\n" + "=" * 80)
        print("[ERROR] Code modified but NO NEW VERSION was created in CHANGELOG.md")
        print("=" * 80)
        print("\nYou must CREATE a new version, not just update existing ones.")
        print("\nHow to add a new version:")
        print("  1. Open CHANGELOG.md")
        print("  2. Add new version entry at the TOP:")
        print("     ## [X.Y.Z] - YYYY-MM-DD")
        print("     ### Changed/Added/Fixed")
        print("     - Description of changes")
        print("  3. Keep [Unreleased] at the very top for future changes")
        print("\nExample:")
        print("  ## [Unreleased]")
        print("")
        print("  ## [2.7.5] - 2026-01-20")
        print("  ### Fixed")
        print("  - Fixed bug in module registry tests")
        print("=" * 80 + "\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
