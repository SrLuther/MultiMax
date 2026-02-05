"""Create fluxo tables

Revision ID: 005
Revises: 004
Create Date: 2026-02-04 23:20:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fluxo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mes_ano", sa.String(length=7), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="aberto"),
        sa.Column("valor_diaria", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fluxo_mes_ano", "fluxo", ["mes_ano"], unique=True)
    op.create_index("ix_fluxo_status", "fluxo", ["status"], unique=False)

    op.create_table(
        "fluxo_ciclo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fluxo_id", sa.Integer(), sa.ForeignKey("fluxo.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fluxo_ciclo_fluxo_id", "fluxo_ciclo", ["fluxo_id"], unique=False)

    op.create_table(
        "fluxo_lancamento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fluxo_id", sa.Integer(), sa.ForeignKey("fluxo.id"), nullable=False),
        sa.Column("ciclo_id", sa.Integer(), sa.ForeignKey("fluxo_ciclo.id"), nullable=False),
        sa.Column("collaborator_id", sa.Integer(), sa.ForeignKey("central_colaborador.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("horas", sa.Float(), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column("observacao", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fluxo_lancamento_fluxo_id", "fluxo_lancamento", ["fluxo_id"], unique=False)
    op.create_index("ix_fluxo_lancamento_ciclo_id", "fluxo_lancamento", ["ciclo_id"], unique=False)
    op.create_index("ix_fluxo_lancamento_collaborator_id", "fluxo_lancamento", ["collaborator_id"], unique=False)

    op.create_table(
        "fluxo_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("valor_diaria", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "fluxo_arquivo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fluxo_id", sa.Integer(), sa.ForeignKey("fluxo.id"), nullable=False),
        sa.Column("collaborator_id", sa.Integer(), sa.ForeignKey("central_colaborador.id"), nullable=False),
        sa.Column("arquivo_path", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fluxo_arquivo_fluxo_id", "fluxo_arquivo", ["fluxo_id"], unique=False)
    op.create_index("ix_fluxo_arquivo_collaborator_id", "fluxo_arquivo", ["collaborator_id"], unique=False)


def downgrade():
    op.drop_index("ix_fluxo_arquivo_collaborator_id", table_name="fluxo_arquivo")
    op.drop_index("ix_fluxo_arquivo_fluxo_id", table_name="fluxo_arquivo")
    op.drop_table("fluxo_arquivo")

    op.drop_table("fluxo_config")

    op.drop_index("ix_fluxo_lancamento_collaborator_id", table_name="fluxo_lancamento")
    op.drop_index("ix_fluxo_lancamento_ciclo_id", table_name="fluxo_lancamento")
    op.drop_index("ix_fluxo_lancamento_fluxo_id", table_name="fluxo_lancamento")
    op.drop_table("fluxo_lancamento")

    op.drop_index("ix_fluxo_ciclo_fluxo_id", table_name="fluxo_ciclo")
    op.drop_table("fluxo_ciclo")

    op.drop_index("ix_fluxo_status", table_name="fluxo")
    op.drop_index("ix_fluxo_mes_ano", table_name="fluxo")
    op.drop_table("fluxo")
