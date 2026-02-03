#!/usr/bin/env python3
import sqlite3

sqlite_db = sqlite3.connect("/opt/multimax-data/estoque.db")
sqlite_cursor = sqlite_db.cursor()

# Verificar estrutura
sqlite_cursor.execute("PRAGMA table_info(holiday)")
cols = sqlite_cursor.fetchall()
print("Colunas em holiday:")
for col in cols:
    print(f"  {col[1]}: {col[2]}")

# Ver dados
sqlite_cursor.execute("SELECT * FROM holiday LIMIT 1")
row = sqlite_cursor.fetchone()
if row:
    print("\nPrimeiro registro:")
    print(row)

sqlite_db.close()
