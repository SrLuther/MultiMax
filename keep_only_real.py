#!/usr/bin/env python3
import psycopg

pg_conn = psycopg.connect("host=multimax-postgres port=5432 dbname=multimax user=multimax password=multimax123")
pg_cur = pg_conn.cursor()

print("Removendo colaboradores de teste...")
pg_cur.execute(
    """
    DELETE FROM colaboradores
    WHERE nome IN ('Joao Silva', 'Maria Santos', 'Pedro Costa', 'Ana Oliveira', 'Carlos Martins')
"""
)
pg_conn.commit()

print("\n✓ Colaboradores restantes:")
pg_cur.execute("SELECT nome, funcao FROM colaboradores ORDER BY nome")
for nome, funcao in pg_cur.fetchall():
    print(f"  - {nome} ({funcao})")

pg_cur.execute("SELECT COUNT(*) FROM colaboradores")
print(f"\n📊 Total: {pg_cur.fetchone()[0]} colaboradores")
