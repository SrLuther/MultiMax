"""
Migration: Fix setor_id NULL values for existing folgas

This migration backfills setor_id for all records that were created before
the setor_id column was added in v2.7.13. This is CRITICAL for the setor
isolation fix to work properly.

Date: 2026-01-21
"""

from alembic import op


def upgrade():
    """
    Backfill setor_id for existing records with NULL values.
    Uses collaborator.setor_id as source.
    """

    # Fix ciclo_folga table
    # Update setor_id by joining with collaborator table
    op.execute(
        """
        UPDATE ciclo_folga
        SET setor_id = (
            SELECT collaborator.setor_id
            FROM collaborator
            WHERE collaborator.id = ciclo_folga.collaborator_id
            LIMIT 1
        )
        WHERE setor_id IS NULL
          AND collaborator_id IS NOT NULL;
    """
    )

    # Fix ciclo_ocorrencia table
    op.execute(
        """
        UPDATE ciclo_ocorrencia
        SET setor_id = (
            SELECT collaborator.setor_id
            FROM collaborator
            WHERE collaborator.id = ciclo_ocorrencia.collaborator_id
            LIMIT 1
        )
        WHERE setor_id IS NULL
          AND collaborator_id IS NOT NULL;
    """
    )

    # Fix ciclo table (all records with setor_id = NULL)
    op.execute(
        """
        UPDATE ciclo
        SET setor_id = (
            SELECT collaborator.setor_id
            FROM collaborator
            WHERE collaborator.id = ciclo.collaborator_id
            LIMIT 1
        )
        WHERE setor_id IS NULL
          AND collaborator_id IS NOT NULL;
    """
    )


def downgrade():
    """
    Downgrade not supported - this is a data fix migration.
    """
    pass
