#!/usr/bin/env python3
import sqlite3

db = sqlite3.connect("estoque_original.db")
cursor = db.cursor()

print("\n[*] Inspecionando banco ORIGINAL da VPS\n")

# Listar tabelas com registros
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = cursor.fetchall()

print("[TABELAS COM DADOS]")
print("=" * 50)

for table_name in sorted([t[0] for t in tables]):
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"  {table_name:30} : {count:5d} registros")

print("=" * 50)

# Verificar setores especificamente
print("\n[SETORES]")
cursor.execute("SELECT id, nome FROM setor LIMIT 10")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Verificar ciclos
print("\n[CICLOS (primeiros 5)]")
cursor.execute("SELECT id, numero_ciclo FROM ciclo LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row[0]}: Ciclo #{row[1]}")

# Verificar colaboradores
print("\n[COLABORADORES (primeiros 5)]")
try:
    cursor.execute("SELECT id, nome FROM collaborator LIMIT 5")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
except Exception:  # noqa: E722
    print("  (tabela collaborator nao encontrada)")

db.close()
