#!/usr/bin/env python3
"""Migração COMPLETA: collaborator + colaboradores -> PostgreSQL"""
import sqlite3

import psycopg

print("Conectando aos bancos...")
sqlite_conn = sqlite3.connect("/opt/multimax-data/estoque.db")
pg_conn = psycopg.connect("host=multimax-postgres port=5432 dbname=multimax user=multimax password=multimax123")

sqlite_cur = sqlite_conn.cursor()
pg_cur = pg_conn.cursor()

# Limpar tabela primeiro
print("Limpando tabela colaboradores...")
pg_cur.execute("TRUNCATE colaboradores CASCADE")
pg_conn.commit()

# Migrar da tabela COLLABORATOR (os açougueiros)
print("\nMigrando da tabela COLLABORATOR...")
sqlite_cur.execute(
    "SELECT name, role, telefone, data_admissao, matricula, departamento FROM collaborator WHERE active = 1"
)
migrados = 0
for row in sqlite_cur.fetchall():
    try:
        name, role, telefone, admissao, matricula, dept = row
        # Gerar CPF fake baseado no ID
        cpf = f"{migrados+10:011d}"

        pg_cur.execute(
            """
            INSERT INTO colaboradores (
                nome, cpf, email, telefone, departamento, funcao,
                data_admissao, ativo, horas_ciclo, saldo_horas,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 40.0, 0.0, NOW(), NOW())
            """,
            (name, cpf, None, telefone, dept or "Açougue", role, admissao, True),
        )
        migrados += 1
        print(f"  + {name} ({role})")
    except Exception as e:
        print(f"Erro {name}: {e}")
        pg_conn.rollback()

pg_conn.commit()
print(f"✓ {migrados} colaboradores migrados de 'collaborator'")

# Migrar da tabela COLABORADORES (teste/demo)
print("\nMigrando da tabela COLABORADORES...")
sqlite_cur.execute("SELECT nome, cpf, email, telefone, departamento, funcao, data_admissao, ativo FROM colaboradores")
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
        print(f"Erro {nome}: {e}")
        pg_conn.rollback()

pg_conn.commit()
print(f"\n✓ TOTAL: {migrados} colaboradores migrados")

# Verificar
pg_cur.execute("SELECT COUNT(*), string_agg(nome, ', ') FROM colaboradores")
count, nomes = pg_cur.fetchone()
print(f"\n📊 PostgreSQL agora tem {count} colaboradores:")
print(f"   {nomes}")

pg_conn.close()
