#!/usr/bin/env python3
import psycopg

pg_conn = psycopg.connect(host="localhost", port=5432, dbname="multimax", user="multimax", password="multimax123")
pg_cursor = pg_conn.cursor()

# Verificar estrutura
pg_cursor.execute(
    """
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'colaboradores'
"""
)
cols = pg_cursor.fetchall()
print("Tabela colaboradores:")
for col in cols:
    print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")

# Verificar constraints
pg_cursor.execute(
    """
    SELECT constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_name = 'colaboradores'
"""
)
constraints = pg_cursor.fetchall()
print("\nConstraints:")
for c in constraints:
    print(f"  {c[0]}: {c[1]}")

pg_cursor.close()
pg_conn.close()
