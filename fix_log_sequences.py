#!/usr/bin/env python3
"""Fix sequences para tabelas de log no PostgreSQL"""
import sys

import psycopg

# Conectar ao banco
try:
    conn = psycopg.connect(
        host="www.multimax.tec.br",
        port=5432,
        dbname="multimax",
        user="multimax",
        password="multimax123",
        sslmode="disable",
    )
    cursor = conn.cursor()

    print("✓ Conectado ao PostgreSQL")

    # Fix para system_log
    cursor.execute("DROP SEQUENCE IF EXISTS system_log_id_seq CASCADE")
    cursor.execute("CREATE SEQUENCE system_log_id_seq START WITH 1")
    max_id = cursor.execute("SELECT COALESCE(MAX(id), 0) FROM system_log").fetchone()[0]
    cursor.execute(f"SELECT setval('system_log_id_seq', {max_id + 1})")
    cursor.execute("ALTER TABLE system_log ALTER COLUMN id SET DEFAULT nextval('system_log_id_seq')")
    print(f"✓ system_log: sequence criada e setada para {max_id + 1}")

    # Fix para log_erros
    cursor.execute("DROP SEQUENCE IF EXISTS log_erros_id_seq CASCADE")
    cursor.execute("CREATE SEQUENCE log_erros_id_seq START WITH 1")
    max_id = cursor.execute("SELECT COALESCE(MAX(id), 0) FROM log_erros").fetchone()[0]
    cursor.execute(f"SELECT setval('log_erros_id_seq', {max_id + 1})")
    cursor.execute("ALTER TABLE log_erros ALTER COLUMN id SET DEFAULT nextval('log_erros_id_seq')")
    print(f"✓ log_erros: sequence criada e setada para {max_id + 1}")

    # Verificar
    cursor.execute(
        """
        SELECT column_name, column_default
        FROM information_schema.columns
        WHERE table_name = 'system_log' AND column_name = 'id'
    """
    )
    col_default = cursor.fetchone()
    print(f"✓ system_log.id DEFAULT: {col_default[1]}")

    conn.commit()
    print("✓ Commit realizado com sucesso!")

except Exception as e:
    print(f"✗ Erro: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    if conn:
        conn.close()
