"""add bulk_id to time_off_record

Revision ID: 010
Revises: 009
Create Date: 2026-02-08
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "time_off_record",
        sa.Column("bulk_id", sa.String(length=36), nullable=True),
    )
    op.create_index("idx_time_off_record_bulk_id", "time_off_record", ["bulk_id"])


def downgrade():
    op.drop_index("idx_time_off_record_bulk_id", table_name="time_off_record")
    op.drop_column("time_off_record", "bulk_id")
