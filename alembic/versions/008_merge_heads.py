"""Merge migration: unify 005_add_couche_b and 007_add_submission_scores heads.

Revision ID: 008_merge_heads
Revises: 005_add_couche_b, 007_add_submission_scores
Create Date: 2026-02-14

Fixes 'Multiple head revisions' CI failure.
Both 005 and 006 branched from 004; 007 followed 006. This merge creates single head.
"""
from __future__ import annotations

revision = '008_merge_heads'
down_revision = ('005_add_couche_b', '007_add_submission_scores')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
