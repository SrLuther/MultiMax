"""
Criação da tabela escala_especial para gerenciar escalas especiais/futuras
Data: 2026-01-22
Versão: v2.8.0+
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app

from multimax import db
from multimax.models import EscalaEspecial


def migrate_up():
    """Cria a tabela escala_especial"""
    try:
        # Cria a tabela se não existir
        db.create_all()
        print("✅ Tabela 'escala_especial' criada com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        return False


def migrate_down():
    """Remove a tabela escala_especial"""
    try:
        db.session.execute("DROP TABLE IF EXISTS escala_especial")
        db.session.commit()
        print("✅ Tabela 'escala_especial' removida com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao remover tabela: {e}")
        db.session.rollback()
        return False


def verify():
    """Verifica se a migração foi aplicada corretamente"""
    try:
        # Tenta criar uma instância para verificar
        result = db.session.execute("SELECT COUNT(*) FROM escala_especial")
        print("✅ Tabela 'escala_especial' existe e está acessível!")
        return True
    except Exception as e:
        print(f"❌ Tabela não existe ou não está acessível: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "down":
            migrate_down()
        elif sys.argv[1] == "verify":
            verify()
        else:
            migrate_up()
    else:
        migrate_up()
