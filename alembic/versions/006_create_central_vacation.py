"""Create central vacation table

Revision ID: 006
Revises: 005
Create Date: 2026-02-05 21:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "central_vacation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collaborator_id", sa.Integer(), sa.ForeignKey("central_colaborador.id"), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("criado_por", sa.String(length=120), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_central_vacation_collaborator_id", "central_vacation", ["collaborator_id"], unique=False)


def downgrade():
    op.drop_index("ix_central_vacation_collaborator_id", table_name="central_vacation")
    op.drop_table("central_vacation")
