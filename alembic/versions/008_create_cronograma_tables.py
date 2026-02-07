"""create cronograma tables

Revision ID: 008
Revises: 007
Create Date: 2026-02-07
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cronograma_bloco",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("setor", sa.String(length=120), nullable=False),
        sa.Column("tipo", sa.String(length=120), nullable=False),
        sa.Column("frequencia", sa.String(length=40), nullable=False),
        sa.Column("ultima_limpeza", sa.Date(), nullable=True),
        sa.Column("proxima_limpeza", sa.Date(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("nome", name="uq_cronograma_bloco_nome"),
    )
    op.create_index("ix_cronograma_bloco_nome", "cronograma_bloco", ["nome"], unique=False)

    op.create_table(
        "cronograma_registro",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bloco_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("equipe", sa.String(length=200), nullable=False),
        sa.Column("observacoes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["bloco_id"], ["cronograma_bloco.id"], name="fk_cronograma_registro_bloco"),
    )
    op.create_index("ix_cronograma_registro_bloco_id", "cronograma_registro", ["bloco_id"], unique=False)
    op.create_index("ix_cronograma_registro_data", "cronograma_registro", ["data"], unique=False)


def downgrade():
    op.drop_index("ix_cronograma_registro_data", table_name="cronograma_registro")
    op.drop_index("ix_cronograma_registro_bloco_id", table_name="cronograma_registro")
    op.drop_table("cronograma_registro")

    op.drop_index("ix_cronograma_bloco_nome", table_name="cronograma_bloco")
    op.drop_table("cronograma_bloco")
