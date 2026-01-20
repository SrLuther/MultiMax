#!/usr/bin/env python3
"""
Script para criar setores e atribuir colaboradores
Execução: python one-time-migrations/2026_01_20_create_setores.py
"""
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from multimax import create_app, db  # noqa: E402
from multimax.models import Collaborator, Setor  # noqa: E402

app = create_app()


def criar_setores():
    """Cria setores padrão"""
    with app.app_context():
        print("=" * 80)
        print("CRIANDO SETORES")
        print("=" * 80)

        # Verificar se já existem setores
        setores_existentes = Setor.query.all()
        if setores_existentes:
            print(f"\n✓ Setores já existem: {len(setores_existentes)}")
            for s in setores_existentes:
                print(f"  - {s.nome} (ativo={s.ativo})")
            return

        # Criar setores padrão
        setores_criar = [
            {"nome": "Açougue", "descricao": "Setor de carnes e produtos de açougue"},
            {"nome": "Estoque", "descricao": "Armazenamento e controle de estoque"},
            {"nome": "Produção", "descricao": "Setor de produção e processamento"},
            {"nome": "Expedição", "descricao": "Empacotamento e expedição de produtos"},
        ]

        for data in setores_criar:
            setor = Setor()
            setor.nome = data["nome"]
            setor.descricao = data["descricao"]
            setor.ativo = True
            db.session.add(setor)
            print(f"\n→ Criando setor: {data['nome']}")

        try:
            db.session.commit()
            print("\n✓ Setores criados com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Erro ao criar setores: {e}")
            return False

        return True


def atribuir_colaboradores():
    """Atribui colaboradores ao setor Açougue"""
    with app.app_context():
        print("\n" + "=" * 80)
        print("ATRIBUINDO COLABORADORES AO SETOR AÇOUGUE")
        print("=" * 80)

        # Buscar setor Açougue
        acougue = Setor.query.filter_by(nome="Açougue").first()
        if not acougue:
            print("\n✗ Setor 'Açougue' não encontrado!")
            return False

        print(f"\nSetor Açougue encontrado (id={acougue.id})")

        # Buscar todos os colaboradores ativos
        colaboradores = Collaborator.query.filter_by(active=True).all()
        print(f"Total de colaboradores ativos: {len(colaboradores)}")

        # Atribuir todos ao Açougue
        atualizados = 0
        for colab in colaboradores:
            if colab.setor_id is None:
                colab.setor_id = acougue.id
                atualizados += 1
                print(f"  ✓ {colab.name} → Açougue")
            else:
                print(f"  - {colab.name} (já tem setor_id={colab.setor_id})")

        if atualizados == 0:
            print("\nTodos os colaboradores já possuem setor atribuído.")
            return True

        try:
            db.session.commit()
            print(f"\n✓ {atualizados} colaboradores atribuídos ao Açougue!")
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Erro ao atribuir colaboradores: {e}")
            return False

        return True


def verificar_resultados():
    """Verifica o resultado final"""
    with app.app_context():
        print("\n" + "=" * 80)
        print("VERIFICAÇÃO FINAL")
        print("=" * 80)

        setores = Setor.query.filter_by(ativo=True).all()
        print(f"\nSetores ativos: {len(setores)}")
        for s in setores:
            print(f"  - {s.nome} (id={s.id})")

        colabs = Collaborator.query.filter_by(active=True).all()
        print(f"\nColaboradores com setor atribuído: {len([c for c in colabs if c.setor_id])}/{len(colabs)}")
        for c in colabs:
            setor_nome = "SEM SETOR"
            if c.setor_id:
                setor = Setor.query.get(c.setor_id)
                if setor:
                    setor_nome = setor.nome
            print(f"  - {c.name}: {setor_nome}")


if __name__ == "__main__":
    try:
        if criar_setores():
            atribuir_colaboradores()

        verificar_resultados()

        print("\n" + "=" * 80)
        print("✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERRO FATAL: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
