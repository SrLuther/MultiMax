#!/usr/bin/env python3
"""Test script to verify _perform_backup is available and works."""

try:
    from multimax import _perform_backup
    print("SUCCESS: _perform_backup imported from multimax")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    exit(1)

try:
    from multimax import create_app
    app = create_app()
    print("SUCCESS: create_app() works")
except Exception as e:
    print(f"ERROR creating app: {type(e).__name__}: {e}")
    exit(1)

try:
    result_daily = _perform_backup(app, daily=True)
    print(f"Daily backup result: {result_daily}")
except Exception as e:
    print(f"ERROR in daily backup: {type(e).__name__}: {e}")

try:
    result_weekly = _perform_backup(app, daily=False)
    print(f"Weekly backup result: {result_weekly}")
except Exception as e:
    print(f"ERROR in weekly backup: {type(e).__name__}: {e}")

print("Test complete")
