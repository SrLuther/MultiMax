#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect("/opt/multimax-data/estoque.db")
cursor = conn.cursor()

print("=" * 60)
print("TABELA: collaborator")
print("=" * 60)
cursor.execute("SELECT * FROM collaborator")
cols = [desc[0] for desc in cursor.description]
print(f"Colunas: {', '.join(cols)}\n")

for row in cursor.fetchall():
    print(row)

print("\n" + "=" * 60)
print("BUSCANDO NOMES ESPECÍFICOS EM TODAS AS TABELAS:")
print("=" * 60)

nomes = ["Diogo", "Natalino", "Edilson", "Welvins", "Renato", "Luciano"]

for nome in nomes:
    print(f"\nProcurando '{nome}':")

    # Buscar em collaborator
    cursor.execute(f"SELECT * FROM collaborator WHERE nome LIKE '%{nome}%'")
    result = cursor.fetchall()
    if result:
        print(f"  ✓ Encontrado em 'collaborator': {result}")

    # Buscar em colaboradores
    cursor.execute(f"SELECT * FROM colaboradores WHERE nome LIKE '%{nome}%'")
    result = cursor.fetchall()
    if result:
        print(f"  ✓ Encontrado em 'colaboradores': {result}")

conn.close()
