#!/usr/bin/env python3
"""
Script de Migração: Adicionar setor_id na tabela collaborator
Versão: 2.6.73
Data: 2026-01-21
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from multimax import create_app, db  # noqa: E402


def migrate_add_setor_to_collaborator():
    """Executa a migração para adicionar setor_id na tabela collaborator"""

    app = create_app()

    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRAÇÃO: Adicionar setor_id à tabela collaborator")
            print("=" * 60)

            # Verificar se a coluna já existe
            result = db.session.execute(db.text("PRAGMA table_info(collaborator)"))
            columns = [row[1] for row in result]

            if "setor_id" in columns:
                print("✓ Coluna 'setor_id' já existe na tabela collaborator")
                print("  Migração não necessária.")
                return

            print("\n1. Adicionando coluna setor_id...")
            db.session.execute(db.text("ALTER TABLE collaborator ADD COLUMN setor_id INTEGER"))
            print("   ✓ Coluna adicionada com sucesso")

            print("\n2. Criando índice para performance...")
            db.session.execute(db.text("CREATE INDEX IF NOT EXISTS ix_collaborator_setor_id ON collaborator(setor_id)"))
            print("   ✓ Índice criado com sucesso")

            # Commit das alterações
            db.session.commit()
            print("\n3. Commit realizado com sucesso")

            # Verificar resultado
            print("\n4. Verificando dados existentes...")
            result = db.session.execute(db.text("SELECT id, name, setor_id FROM collaborator LIMIT 5"))
            rows = result.fetchall()

            if rows:
                print("\n   Primeiros 5 colaboradores:")
                print("   " + "-" * 50)
                for row in rows:
                    print(f"   ID: {row[0]:<4} | Nome: {row[1]:<30} | Setor: {row[2] or 'Não definido'}")
                print("   " + "-" * 50)
            else:
                print("   Nenhum colaborador encontrado no banco")

            print("\n" + "=" * 60)
            print("✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            print("\nPróximos passos:")
            print("1. Acesse a página de Gestão de Colaboradores")
            print("2. Edite cada colaborador e selecione seu setor")
            print("3. Os novos lançamentos herdarão automaticamente o setor")
            print()

        except Exception as e:
            db.session.rollback()
            print(f"\n✗ ERRO durante a migração: {e}")
            print("\nA migração foi revertida (rollback)")
            sys.exit(1)


if __name__ == "__main__":
    migrate_add_setor_to_collaborator()
