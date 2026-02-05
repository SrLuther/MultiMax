"""create setor_cargo table

Revision ID: 007
Revises: 006
Create Date: 2026-02-05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "setor_cargo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("setor_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["setor_id"], ["setor.id"], name="fk_setor_cargo_setor"),
        sa.UniqueConstraint("setor_id", "nome", name="uq_setor_cargo_nome"),
    )
    op.create_index("ix_setor_cargo_setor_id", "setor_cargo", ["setor_id"], unique=False)
    op.create_index("ix_setor_cargo_nome", "setor_cargo", ["nome"], unique=False)


def downgrade():
    op.drop_index("ix_setor_cargo_nome", table_name="setor_cargo")
    op.drop_index("ix_setor_cargo_setor_id", table_name="setor_cargo")
    op.drop_table("setor_cargo")
