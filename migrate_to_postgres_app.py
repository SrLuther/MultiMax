#!/usr/bin/env python3
"""Script de migração: SQLite antigo -> PostgreSQL novo."""

import os
import sqlite3
import sys

# noqa: E402 - These imports require modified sys.path and environment
sys.path.insert(0, "/opt/multimax")  # noqa: E402
os.environ["DATABASE_URL"] = "postgresql://multimax:multimax123@localhost:5432/multimax?sslmode=disable"  # noqa: E402

from multimax import create_app, db  # noqa: E402
from multimax.models import CicloSemanal, Colaborador, Setor  # noqa: E402

print("\n[*] Iniciando migração: estoque.db (SQLite) -> PostgreSQL\n")

# Criar app Flask
app = create_app()

with app.app_context():
    # 1. Conectar ao SQLite antigo
    print("[*] Conectando ao banco SQLite antigo...")
    try:
        sqlite_db = sqlite3.connect("/opt/multimax-data/estoque.db")
        sqlite_cursor = sqlite_db.cursor()
        print("[OK] Conectado ao SQLite\n")
    except Exception as e:
        print(f"[ERRO] Nao conseguiu conectar ao SQLite: {e}\n")
        exit(1)

    # 2. Migrar Setores
    print("[*] Migrando Setores...")
    try:
        sqlite_cursor.execute("SELECT id, nome FROM setor WHERE ativo = 1")
        setores = sqlite_cursor.fetchall()

        setores_inseridos = 0
        for setor_id, nome in setores:
            # Verificar se ja existe
            if not Setor.query.filter_by(nome=nome).first():
                setor = Setor(nome=nome, descricao=f"Setor: {nome}", ativo=True)
                db.session.add(setor)
                setores_inseridos += 1
                print(f"  [+] {nome}")
            else:
                print(f"  [SKIP] {nome} (ja existe)")

        db.session.commit()
        print(f"[OK] {setores_inseridos} setores migrados\n")
    except Exception as e:
        db.session.rollback()
        print(f"[ERRO] ao migrar setores: {e}\n")

    # 3. Migrar Ciclos Semanais
    print("[*] Migrando Ciclos Semanais...")
    try:
        # Tentar tabela ciclo_semana (novo nome) ou ciclo_semana
        try:
            sqlite_cursor.execute("SELECT id, numero_ciclo, data_inicio, data_fim FROM ciclos_semanais")
        except Exception:  # noqa: E722
            sqlite_cursor.execute("SELECT id, numero_ciclo, data_inicio, data_fim FROM ciclo_semana")

        ciclos = sqlite_cursor.fetchall()

        ciclos_inseridos = 0
        for ciclo_id, numero_ciclo, data_inicio, data_fim in ciclos:
            if not CicloSemanal.query.filter_by(numero_ciclo=numero_ciclo).first():
                ciclo = CicloSemanal(
                    numero_ciclo=numero_ciclo, data_inicio=data_inicio, data_fim=data_fim, ativo=True, observacoes=None
                )
                db.session.add(ciclo)
                ciclos_inseridos += 1

        db.session.commit()
        print(f"[OK] {ciclos_inseridos} ciclos semanais migrados\n")
    except Exception as e:
        db.session.rollback()
        print(f"[ERRO] ao migrar ciclos semanais: {e}\n")

    # 4. Migrar Colaboradores
    print("[*] Migrando Colaboradores...")
    try:
        # Extrair nomes unicos de colaboradores
        sqlite_cursor.execute(
            """
            SELECT DISTINCT nome FROM (
                SELECT nome FROM collaborator WHERE nome IS NOT NULL
                UNION
                SELECT nome_colaborador FROM ciclo WHERE nome_colaborador IS NOT NULL
            ) as temp
            ORDER BY nome
        """
        )

        colaboradores = sqlite_cursor.fetchall()
        colaboradores_inseridos = 0

        for (nome,) in colaboradores:
            if nome and nome.strip():
                nome = nome.strip()
                if not Colaborador.query.filter_by(nome=nome).first():
                    # CPF dummy
                    cpf = f"000.000.000-{str(colaboradores_inseridos).zfill(2)}"
                    colab = Colaborador(
                        nome=nome,
                        cpf=cpf,
                        funcao="Colaborador",
                        departamento="Operacional",
                        ativo=True,
                        horas_ciclo=40.0,
                        saldo_horas=0.0,
                    )
                    db.session.add(colab)
                    colaboradores_inseridos += 1
                    print(f"  [+] {nome}")

        db.session.commit()
        print(f"[OK] {colaboradores_inseridos} colaboradores migrados\n")
    except Exception as e:
        db.session.rollback()
        print(f"[ERRO] ao migrar colaboradores: {e}\n")

    # 5. Verificacao final
    print("[VERIFICACAO FINAL - POSTGRESQL]")
    print("=" * 50)

    print(f"  Setores: {Setor.query.count()}")
    print(f"  Ciclos Semanais: {CicloSemanal.query.count()}")
    print(f"  Colaboradores: {Colaborador.query.count()}")

    print("=" * 50)

    sqlite_db.close()

print("\n[OK] Migracao concluida!\n")
