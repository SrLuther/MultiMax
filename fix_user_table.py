#!/usr/bin/env python3
import psycopg

conn = psycopg.connect(
    host="www.multimax.tec.br", port=5432, dbname="multimax", user="multimax", password="multimax123", sslmode="disable"
)

cursor = conn.cursor()

try:
    # Rollback first
    conn.rollback()

    seq_name = "user_id_seq"
    table_name = "user"

    # Drop se existir
    cursor.execute(f"DROP SEQUENCE IF EXISTS {seq_name} CASCADE")

    # Criar nova sequence
    cursor.execute(f"CREATE SEQUENCE {seq_name} START WITH 1")

    # Pegar max id atual
    cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
    result = cursor.fetchone()
    max_id = int(result[0]) if result and result[0] is not None else 0

    print(f"Max ID from 'user' table: {max_id}")

    # Setvar sequência
    cursor.execute(f"SELECT setval('{seq_name}', {max_id + 1})")

    # Aplicar DEFAULT
    cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN id SET DEFAULT nextval('{seq_name}'::regclass)")

    conn.commit()
    print(f"✓ 'user' table fixed successfully!")

except Exception as e:
    print(f"✗ Error: {e}")
    conn.rollback()

conn.close()
