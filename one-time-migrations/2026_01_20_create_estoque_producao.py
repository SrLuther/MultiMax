#!/usr/bin/env python3
"""
Migração: Criação de tabelas para Estoque de Produção com Previsão de Uso
Data: 2026-01-20
Descrição:
    - Cria tabela estoque_producao para registrar produtos produzidos e estocados
    - Cria tabela historico_ajuste_estoque para auditoria de ajustes
    - Relaciona com produtos, setores
    - Inclui controle de previsão de uso (ex: eventos sazonais)
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from multimax import create_app, db  # noqa: E402
from multimax.models import EstoqueProducao, HistoricoAjusteEstoque  # noqa: E402

app = create_app()


def migrate():
    """Executa a migração para criar as tabelas de estoque de produção"""
    with app.app_context():
        try:
            print("=" * 80)
            print("MIGRAÇÃO: Estoque de Produção com Previsão de Uso")
            print("=" * 80)

            # Verifica se as tabelas já existem
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()

            if "estoque_producao" in existing_tables:
                print("⚠️  Tabela 'estoque_producao' já existe. Pulando criação...")
            else:
                print("\n📦 Criando tabela 'estoque_producao'...")
                EstoqueProducao.__table__.create(db.engine)
                print("✅ Tabela 'estoque_producao' criada com sucesso!")

            if "historico_ajuste_estoque" in existing_tables:
                print("⚠️  Tabela 'historico_ajuste_estoque' já existe. Pulando criação...")
            else:
                print("\n📋 Criando tabela 'historico_ajuste_estoque'...")
                HistoricoAjusteEstoque.__table__.create(db.engine)
                print("✅ Tabela 'historico_ajuste_estoque' criada com sucesso!")

            db.session.commit()
            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\nPróximos passos:")
            print("1. Reinicie o aplicativo")
            print("2. Acesse o menu 'Estoque de Produção'")
            print("3. Comece a registrar produtos produzidos")
            print("\n")

        except Exception as e:
            print(f"\n❌ ERRO durante a migração: {e}")
            print("\n🔄 Executando rollback...")
            db.session.rollback()

            # Tenta remover as tabelas criadas
            try:
                if "estoque_producao" in inspector.get_table_names():
                    EstoqueProducao.__table__.drop(db.engine)
                    print("   ↪️  Tabela 'estoque_producao' removida")
                if "historico_ajuste_estoque" in inspector.get_table_names():
                    HistoricoAjusteEstoque.__table__.drop(db.engine)
                    print("   ↪️  Tabela 'historico_ajuste_estoque' removida")
            except Exception as rollback_error:
                print(f"   ⚠️  Erro no rollback: {rollback_error}")

            print("\n❌ Migração falhou. Nenhuma alteração foi aplicada.")
            sys.exit(1)


def rollback():
    """Remove as tabelas criadas (rollback)"""
    with app.app_context():
        try:
            print("=" * 80)
            print("ROLLBACK: Removendo tabelas de Estoque de Produção")
            print("=" * 80)

            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()

            if "historico_ajuste_estoque" in existing_tables:
                print("\n🗑️  Removendo tabela 'historico_ajuste_estoque'...")
                HistoricoAjusteEstoque.__table__.drop(db.engine)
                print("✅ Tabela 'historico_ajuste_estoque' removida!")

            if "estoque_producao" in existing_tables:
                print("\n🗑️  Removendo tabela 'estoque_producao'...")
                EstoqueProducao.__table__.drop(db.engine)
                print("✅ Tabela 'estoque_producao' removida!")

            print("\n✅ ROLLBACK CONCLUÍDO!")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ ERRO durante rollback: {e}")
            sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migração de Estoque de Produção")
    parser.add_argument("--rollback", action="store_true", help="Executa rollback (remove as tabelas criadas)")
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
