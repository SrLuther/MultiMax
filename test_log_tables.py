#!/usr/bin/env python3
import psycopg

conn = psycopg.connect(
    host="www.multimax.tec.br", port=5432, dbname="multimax", user="multimax", password="multimax123", sslmode="disable"
)

cursor = conn.cursor()

# Test functions from /gestao
tables_to_test = [
    ("historico", "Historico table"),
    ("cleaning_history", "CleaningHistory table"),
    ("system_log", "SystemLog table"),
]

for table, desc in tables_to_test:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table} LIMIT 1")
        count = cursor.fetchone()[0]
        print(f"✓ {desc}: OK ({count} rows)")
    except Exception as e:
        print(f"✗ {desc}: ERROR - {e}")

conn.close()
