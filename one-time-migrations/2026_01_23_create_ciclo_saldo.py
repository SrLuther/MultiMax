#!/usr/bin/env python3
"""
Script para criar tabela ciclo_saldo
Execução: python one-time-migrations/2026_01_23_create_ciclo_saldo.py
"""
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from multimax import create_app, db  # noqa: E402
from multimax.models import CicloSaldo  # noqa: E402

app = create_app()


def criar_ciclo_saldo():
    """Cria tabela ciclo_saldo se não existir"""
    with app.app_context():
        print("=" * 80)
        print("CRIANDO TABELA ciclo_saldo")
        print("=" * 80)

        # Verificar se tabela já existe
        inspector = db.inspect(db.engine)
        tabelas = inspector.get_table_names()

        if "ciclo_saldo" in tabelas:
            print("\n✓ Tabela 'ciclo_saldo' já existe")
            registros = CicloSaldo.query.count()
            print(f"  - Total de registros: {registros}")
            return

        print("\n→ Criando tabela 'ciclo_saldo'...")
        try:
            # Criar tabela a partir do modelo
            db.create_all()

            print("\n✓ Tabela 'ciclo_saldo' criada com sucesso")
            print("\nEstrutura da tabela:")
            print("  - id: Integer (PK)")
            print("  - collaborator_id: Integer (FK → collaborator.id)")
            print("  - mes_ano: String(7) [formato: MM-YYYY]")
            print("  - saldo: Numeric(5,1) [em horas]")
            print("  - created_at: DateTime")
            print("  - created_by: String(100)")
            print("  - updated_at: DateTime")
            print("  - updated_by: String(100)")
            print("  - Constraint: UNIQUE (collaborator_id, mes_ano)")

            db.session.commit()
            print("\n✓ Operação concluída com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Erro ao criar tabela: {e}")
            raise


if __name__ == "__main__":
    criar_ciclo_saldo()
