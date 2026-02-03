#!/usr/bin/env python3
"""Migração limpa: SQLite -> PostgreSQL"""
import sqlite3

import psycopg

print("Conectando aos bancos...")
sqlite_conn = sqlite3.connect("/opt/multimax-data/estoque.db")
pg_conn = psycopg.connect("host=multimax-postgres port=5432 dbname=multimax user=multimax password=multimax123")

sqlite_cur = sqlite_conn.cursor()
pg_cur = pg_conn.cursor()

# Migrar colaboradores
print("Migrando colaboradores...")
sqlite_cur.execute("SELECT nome, cpf, email, telefone, departamento, funcao, data_admissao, ativo FROM colaboradores")
migrados = 0
for row in sqlite_cur.fetchall():
    try:
        nome, cpf, email, telefone, dept, funcao, admissao, ativo = row
        pg_cur.execute(
            """
            INSERT INTO colaboradores (
                nome, cpf, email, telefone, departamento, funcao,
                data_admissao, ativo, horas_ciclo, saldo_horas,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 40.0, 0.0, NOW(), NOW())
            """,
            (nome, cpf, email, telefone, dept, funcao, admissao, bool(ativo)),
        )
        migrados += 1
        print(f"  + {nome}")
    except Exception as e:
        print(f"Colaborador {nome}: {e}")
        pg_conn.rollback()

pg_conn.commit()
print(f"✓ {migrados} colaboradores migrados")

# Migrar setores
print("Migrando setores...")
sqlite_cur.execute("SELECT nome, ativo FROM setor")
migrados = 0
for nome, ativo in sqlite_cur.fetchall():
    try:
        pg_cur.execute(
            """
            INSERT INTO setor (nome, descricao, ativo, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            """,
            (nome, f"Setor {nome}", bool(ativo)),
        )
        migrados += 1
        print(f"  + {nome}")
    except Exception as e:
        print(f"Setor {nome}: {e}")
        pg_conn.rollback()

pg_conn.commit()
print(f"✓ {migrados} setores migrados")

print("\n✓ Migração concluída!")
