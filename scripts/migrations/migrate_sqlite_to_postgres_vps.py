#!/usr/bin/env python3
"""
Script de migração: SQLite antigo (estoque.db) -> PostgreSQL novo
Extrai dados de setores, ciclos e colaboradores do banco antigo
"""

import sqlite3
from datetime import datetime

import psycopg

# Configuração
SQLITE_DB = "/opt/multimax-data/estoque.db"
POSTGRES_CONNECTION = "postgresql://multimax:multimax123@localhost:5432/multimax"

print("\n[*] Iniciando migração SQLite -> PostgreSQL\n")

# 1. Conectar ao SQLite antigo
print("[*] Conectando ao banco SQLite antigo...")
try:
    sqlite_db = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_db.cursor()
    print("[OK] Conectado ao SQLite\n")
except Exception as e:
    print(f"[ERRO] Nao conseguiu conectar ao SQLite: {e}\n")
    exit(1)

# 2. Conectar ao PostgreSQL novo
print("[*] Conectando ao PostgreSQL novo...")
try:
    pg_conn = psycopg.connect(POSTGRES_CONNECTION)
    pg_cursor = pg_conn.cursor()
    print("[OK] Conectado ao PostgreSQL\n")
except Exception as e:
    print(f"[ERRO] Nao conseguiu conectar ao PostgreSQL: {e}\n")
    exit(1)

# 3. Migrar Setores
print("[*] Migrando Setores...")
try:
    sqlite_cursor.execute("SELECT id, nome FROM setor WHERE ativo = 1")
    setores = sqlite_cursor.fetchall()

    # Verificar quais setores ja existem
    pg_cursor.execute("SELECT nome FROM public.setor")
    existing_setores = {row[0] for row in pg_cursor.fetchall()}

    setores_inseridos = 0
    for setor_id, nome in setores:
        # Se nao existe, inserir
        if nome not in existing_setores:
            pg_cursor.execute(
                "INSERT INTO public.setor (nome, descricao, ativo) VALUES (%s, %s, %s)", (nome, f"Setor: {nome}", True)
            )
            setores_inseridos += 1
            print(f"  [+] {nome}")
        else:
            print(f"  [SKIP] {nome} (ja existe)")

    pg_conn.commit()
    print(f"[OK] {setores_inseridos} setores migrados\n")
except Exception as e:
    print(f"[ERRO] ao migrar setores: {e}\n")
    pg_conn.rollback()

# 4. Migrar Ciclos Semanais (da tabela ciclo_semana do SQLite)
print("[*] Migrando Ciclos Semanais...")
try:
    sqlite_cursor.execute("SELECT id, numero_ciclo, data_inicio, data_fim FROM ciclo_semana LIMIT 26")
    ciclos = sqlite_cursor.fetchall()

    ciclos_inseridos = 0
    for ciclo_id, numero_ciclo, data_inicio, data_fim in ciclos:
        try:
            pg_cursor.execute(
                """INSERT INTO public.ciclos_semanais
                   (numero_ciclo, data_inicio, data_fim, ativo, observacoes, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (numero_ciclo) DO NOTHING""",
                (numero_ciclo, data_inicio, data_fim, True, None, datetime.now(), datetime.now()),
            )
            ciclos_inseridos += 1
        except Exception:  # noqa: E722
            pass  # Skip se ja existe

    pg_conn.commit()
    print(f"[OK] {ciclos_inseridos} ciclos semanais migrados\n")
except Exception as e:
    print(f"[ERRO] ao migrar ciclos semanais: {e}\n")
    pg_conn.rollback()

# 5. Migrar Colaboradores
print("[*] Migrando Colaboradores...")
try:
    # Tentar na tabela collaborator ou no legado
    sqlite_cursor.execute(
        """
        SELECT DISTINCT nome FROM (
            SELECT nome FROM collaborator
            UNION ALL
            SELECT nome_colaborador FROM ciclo
        ) as combined
        LIMIT 20
    """
    )
    colaboradores = sqlite_cursor.fetchall()

    colaboradores_inseridos = 0
    for (nome,) in colaboradores:
        if nome and nome.strip():
            try:
                pg_cursor.execute(
                    """INSERT INTO public.colaboradores
                       (nome, cpf, funcao, departamento, ativo, horas_ciclo, saldo_horas, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (cpf) DO NOTHING""",
                    (
                        nome.strip(),
                        f'CPF-{nome.replace(" ", "-")}',
                        "Colaborador",
                        "Operacional",
                        True,
                        40.0,
                        0.0,
                        datetime.now(),
                        datetime.now(),
                    ),
                )
                colaboradores_inseridos += 1
                print(f"  [+] {nome}")
            except Exception:
                pass  # Skip se ja existe

    pg_conn.commit()
    print(f"[OK] {colaboradores_inseridos} colaboradores migrados\n")
except Exception as e:
    print(f"[ERRO] ao migrar colaboradores: {e}\n")
    pg_conn.rollback()

# 6. Verificacao final
print("[VERIFICACAO FINAL]")
print("=" * 50)

pg_cursor.execute("SELECT COUNT(*) FROM public.setor")
result = pg_cursor.fetchone()
print(f"  Setores: {result[0] if result else 0}")

pg_cursor.execute("SELECT COUNT(*) FROM public.ciclos_semanais")
result = pg_cursor.fetchone()
print(f"  Ciclos Semanais: {result[0] if result else 0}")

pg_cursor.execute("SELECT COUNT(*) FROM public.colaboradores")
result = pg_cursor.fetchone()
print(f"  Colaboradores: {result[0] if result else 0}")

print("=" * 50)

# Fechar conexoes
sqlite_db.close()
pg_conn.close()

print("\n[OK] Migracao concluida!\n")
