#!/usr/bin/env python3
import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "multimax.db")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Verificar tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    print("📊 Tabelas no banco SQLite:")
    if not tables:
        print("  (vazio)")
    else:
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table[0]}"')
                count = cursor.fetchone()[0]
                print(f"  - {table[0]}: {count} registros")
            except Exception as e:
                print(f"  - {table[0]}: ERRO - {e}")

    conn.close()
else:
    print(f"❌ Arquivo {db_path} não encontrado")
