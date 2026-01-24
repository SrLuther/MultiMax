#!/usr/bin/env python3
from multimax import _perform_backup, create_app
import os

app = create_app()

# Diagnóstico
backups_dir = app.config.get("BACKUP_DIR")
db_file = app.config.get("DB_FILE_PATH")
print(f"Backups dir: {backups_dir}")
print(f"DB file: {db_file}")
print(f"Dir exists: {os.path.exists(backups_dir)}")
print(f"Dir writable: {os.access(backups_dir, os.W_OK)}")
print(f"DB exists: {os.path.exists(db_file)}")

# Testar backup
try:
    print("\nTesting daily backup...")
    result = _perform_backup(app, daily=True)
    print(f"Daily result: {result}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Listar arquivos
print("\nBackup files:")
try:
    for f in os.listdir(backups_dir):
        path = os.path.join(backups_dir, f)
        size = os.path.getsize(path)
        print(f"  {f}: {size} bytes")
except Exception as e:
    print(f"Error listing: {e}")
