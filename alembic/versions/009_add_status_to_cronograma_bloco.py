"""add status_atual to cronograma_bloco

Revision ID: 009
Revises: 008
Create Date: 2026-02-07
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cronograma_bloco", sa.Column("status_atual", sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column("cronograma_bloco", "status_atual")
