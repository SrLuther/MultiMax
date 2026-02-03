"""Add setor_id columns to ciclo models

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    """Add setor_id columns to ciclo_semana"""

    # Add setor_id to ciclo_semana - SQLite needs special handling
    with op.batch_alter_table("ciclo_semana", schema=None) as batch_op:
        batch_op.add_column(sa.Column("setor_id", sa.Integer(), nullable=True, server_default="1"))
        batch_op.create_index("ix_ciclo_semana_setor_id", ["setor_id"], unique=False)
        batch_op.create_foreign_key("fk_ciclo_semana_setor_id", "setor", ["setor_id"], ["id"])


def downgrade():
    """Remove setor_id columns"""

    with op.batch_alter_table("ciclo_semana", schema=None) as batch_op:
        batch_op.drop_index("ix_ciclo_semana_setor_id")
        batch_op.drop_column("setor_id")
