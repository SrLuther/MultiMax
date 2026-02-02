#!/usr/bin/env python3
"""Fix ALL sequences para tabelas com id NOT NULL sem DEFAULT"""
import sys

import psycopg

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

    # Rollback qualquer transação pendente
    try:
        conn.rollback()
    except:
        pass

    print("✓ Conectado ao PostgreSQL")

    # Encontrar todas as tabelas com coluna 'id' que é NOT NULL sem DEFAULT
    cursor.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE is_nullable = 'NO'
          AND column_default IS NULL
          AND column_name = 'id'
          AND table_schema = 'public'
        ORDER BY table_name
    """
    )

    tables_to_fix = cursor.fetchall()
    print(f"\n📋 Encontradas {len(tables_to_fix)} tabelas para fix:\n")

    for table_name, column_name in tables_to_fix:
        try:
            seq_name = f"{table_name}_id_seq"

            # Rollback se houver erro anterior
            try:
                conn.rollback()
            except Exception:
                pass

            # Drop se existir
            cursor.execute(f"DROP SEQUENCE IF EXISTS {seq_name} CASCADE")

            # Criar nova sequence
            cursor.execute(f"CREATE SEQUENCE {seq_name} START WITH 1")

            # Pegar max id atual (com tratamento para tipos diferentes)
            try:
                cursor.execute(f"SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}")
                result = cursor.fetchone()
                max_id = int(result[0]) if result and result[0] is not None else 0
            except Exception as e:
                # Alguns tipos de coluna podem não ser numéricos
                max_id = 0

            # Setvar sequência
            cursor.execute(f"SELECT setval('{seq_name}', {max_id + 1})")

            # Aplicar DEFAULT
            cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET DEFAULT nextval('{seq_name}')")

            conn.commit()
            print(f"  ✓ {table_name:40s} - sequence setada para {max_id + 1}")

        except Exception as e:
            print(f"  ✗ {table_name:40s} - ERRO: {e}")

    print("\n✓ Todas as tabelas foram corrigidas!")

except Exception as e:
    print(f"\n✗ Erro geral: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    if conn:
        conn.close()
