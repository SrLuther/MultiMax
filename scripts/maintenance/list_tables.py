#!/usr/bin/env python3
import psycopg

pg_conn = psycopg.connect(host="localhost", port=5432, dbname="multimax", user="multimax", password="multimax123")
pg_cursor = pg_conn.cursor()

# Listar tabelas
pg_cursor.execute(
    """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
"""
)
tables = pg_cursor.fetchall()
print("Tabelas no banco:")
for table in tables:
    pg_cursor.execute(f'SELECT COUNT(*) FROM "{table[0]}"')
    count = pg_cursor.fetchone()[0]
    print(f"  {table[0]}: {count} registros")

pg_cursor.close()
pg_conn.close()
