"""
Migração One-Time: Adicionar coluna setor_id nas tabelas ciclo_folga e ciclo_ocorrencia

Data: 2026-01-21
Motivo: O modelo foi atualizado com setor_id mas as tabelas do banco não foram atualizadas
"""

import os
import sys

# Ajustar path para importar módulos do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multimax import create_app, db  # noqa: E402
from multimax.models import CicloFolga, CicloOcorrencia, Collaborator  # noqa: E402


def migrate():
    """Adiciona coluna setor_id e popula com valores dos colaboradores"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se as colunas já existem
            inspector = db.inspect(db.engine)

            # Migração para ciclo_folga
            columns_folga = [col["name"] for col in inspector.get_columns("ciclo_folga")]
            if "setor_id" not in columns_folga:
                print("Adicionando coluna setor_id em ciclo_folga...")
                # SQLite não suporta ALTER TABLE ADD COLUMN com NOT NULL e FK diretamente
                # Primeiro adicionar como nullable
                db.session.execute(db.text("ALTER TABLE ciclo_folga ADD COLUMN setor_id INTEGER"))
                db.session.commit()

                # Atualizar registros existentes com setor do colaborador
                print("Atualizando setor_id para registros existentes em ciclo_folga...")
                folgas = CicloFolga.query.all()
                for folga in folgas:
                    colab = Collaborator.query.get(folga.collaborator_id)
                    if colab and colab.setor_id:
                        folga.setor_id = colab.setor_id
                    else:
                        # Se não tiver setor, usar setor padrão (ID 1 - assumindo que existe)
                        folga.setor_id = 1
                db.session.commit()
                print(f"✓ {len(folgas)} registros atualizados em ciclo_folga")
            else:
                print("✓ Coluna setor_id já existe em ciclo_folga")

            # Migração para ciclo_ocorrencia
            columns_ocorrencia = [col["name"] for col in inspector.get_columns("ciclo_ocorrencia")]
            if "setor_id" not in columns_ocorrencia:
                print("\nAdicionando coluna setor_id em ciclo_ocorrencia...")
                db.session.execute(db.text("ALTER TABLE ciclo_ocorrencia ADD COLUMN setor_id INTEGER"))
                db.session.commit()

                # Atualizar registros existentes com setor do colaborador
                print("Atualizando setor_id para registros existentes em ciclo_ocorrencia...")
                ocorrencias = CicloOcorrencia.query.all()
                for ocorrencia in ocorrencias:
                    colab = Collaborator.query.get(ocorrencia.collaborator_id)
                    if colab and colab.setor_id:
                        ocorrencia.setor_id = colab.setor_id
                    else:
                        # Se não tiver setor, usar setor padrão (ID 1)
                        ocorrencia.setor_id = 1
                db.session.commit()
                print(f"✓ {len(ocorrencias)} registros atualizados em ciclo_ocorrencia")
            else:
                print("✓ Coluna setor_id já existe em ciclo_ocorrencia")

            print("\n✅ Migração concluída com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro na migração: {e}")
            import traceback

            traceback.print_exc()
            return False
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("Migração: Adicionar setor_id em ciclo_folga e ciclo_ocorrencia")
    print("=" * 70)
    migrate()
