"""Create central tables

Revision ID: 004
Revises: 003
Create Date: 2026-02-04 09:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "central_colaborador",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("cargo", sa.String(length=120), nullable=True),
        sa.Column("setor", sa.String(length=120), nullable=True),
        sa.Column("permissao", sa.String(length=20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(length=120), nullable=True),
        sa.Column("last_password_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_central_colaborador_nome", "central_colaborador", ["nome"], unique=False)
    op.create_index("ix_central_colaborador_username", "central_colaborador", ["username"], unique=True)
    op.create_index("ix_central_colaborador_permissao", "central_colaborador", ["permissao"], unique=False)

    op.create_table(
        "central_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("target_nome", sa.String(length=120), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_central_log_created_at", "central_log", ["created_at"], unique=False)


def downgrade():
    op.drop_index("ix_central_log_created_at", table_name="central_log")
    op.drop_table("central_log")

    op.drop_index("ix_central_colaborador_permissao", table_name="central_colaborador")
    op.drop_index("ix_central_colaborador_username", table_name="central_colaborador")
    op.drop_index("ix_central_colaborador_nome", table_name="central_colaborador")
    op.drop_table("central_colaborador")
