"""Add regular_team column to colaborador table

Revision ID: 003
Revises: 002
Create Date: 2026-02-03 15:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    """Add regular_team column to colaborador table"""

    # Add regular_team to colaborador
    with op.batch_alter_table("colaboradores", schema=None) as batch_op:
        batch_op.add_column(sa.Column("regular_team", sa.String(length=1), nullable=True))
        batch_op.create_index(
            "ix_colaboradores_regular_team",
            ["regular_team"],
            unique=False,
        )


def downgrade():
    """Remove regular_team column"""

    with op.batch_alter_table("colaboradores", schema=None) as batch_op:
        batch_op.drop_index("ix_colaboradores_regular_team")
        batch_op.drop_column("regular_team")
