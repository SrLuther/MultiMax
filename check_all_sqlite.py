#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect("/opt/multimax-data/estoque.db")
cursor = conn.cursor()

# Listar todas as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tabelas = [row[0] for row in cursor.fetchall()]

print("=" * 60)
print("TABELAS NO BANCO:")
print("=" * 60)
for tabela in tabelas:
    if tabela.startswith("sqlite_"):
        continue
    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
    count = cursor.fetchone()[0]
    print(f"{tabela:30s} -> {count:5d} registros")

print("\n" + "=" * 60)
print("TODOS OS COLABORADORES:")
print("=" * 60)
cursor.execute("SELECT * FROM colaboradores")
cols = [desc[0] for desc in cursor.description]
print(f"Colunas: {', '.join(cols)}")
print("-" * 60)
for row in cursor.fetchall():
    print(row)

conn.close()
