# STUB — Cette migration réconcilie une révision présente en DB locale
# (`098_primary_admin_email_owner_mandate`) mais absente du graphe du repo.
# Aucune opération de schéma.
# Investigation 2026-04-15 (CTO D-07) : le fichier historique existe dans
# `git show dc975355:alembic/versions/098_primary_admin_email_owner_mandate.py`
# (branche auth) ; la chaîne 096→097→098 n’est pas dans `main` actuel.
# Si votre `alembic_version` contient encore l’ancien id, exécuter :
#   UPDATE alembic_version
#   SET version_num = '098_primary_admin_email_owner_mandate_stub'
#   WHERE version_num = '098_primary_admin_email_owner_mandate';
# À investiguer après Phase 2 pour aligner données / historique si besoin.

from __future__ import annotations

revision = "098_primary_admin_email_owner_mandate_stub"
down_revision = "093_v51_assessment_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
