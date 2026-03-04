"""
m5_cleanup_a_committee_event_type_check

Met à jour la CHECK constraint committee_events.event_type :
  recommendation_set → review_opened

Contexte :
  M5-CLEANUP-A a renommé l'event dans service.py + models.py.
  La CHECK constraint DB n'avait pas été alignée.
  Cette migration solde la cohérence code ↔ schéma DB.

Conformité Constitution §1.2 :
  "recommendation_set" = terminologie moteur de recommandation
  "review_opened"      = terminologie processus humain · correct

Idempotence :
  Si review_opened est déjà dans la liste → skip propre.
  Si la contrainte est absente → skip propre.

Révision     : m5_cleanup_a_committee_event_type_check
Down revision: m5_fix_market_signals_vendor_type
"""

revision = "m5_cleanup_a_committee_event_type_check"
down_revision = "m5_fix_market_signals_vendor_type"
branch_labels = None
depends_on = None

from alembic import op

_CONSTRAINT_NAME = "committee_events_event_type_check"
_TABLE_NAME = "committee_events"

_VALID_EVENT_TYPES_NEW = [
    "committee_created",
    "member_added",
    "member_removed",
    "meeting_opened",
    "vote_recorded",
    "review_opened",
    "seal_requested",
    "seal_completed",
    "seal_rejected",
    "snapshot_emitted",
    "committee_cancelled",
]

_VALID_EVENT_TYPES_OLD = [
    "committee_created",
    "member_added",
    "member_removed",
    "meeting_opened",
    "vote_recorded",
    "recommendation_set",
    "seal_requested",
    "seal_completed",
    "seal_rejected",
    "snapshot_emitted",
    "committee_cancelled",
]


def _build_array_literal(values: list) -> str:
    """Construit ARRAY['v1', 'v2', ...] compatible PL/pgSQL EXECUTE $q$...$q$."""
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"ARRAY[{quoted}]"


def upgrade() -> None:
    new_array = _build_array_literal(_VALID_EVENT_TYPES_NEW)
    op.execute(f"""
        DO $$
        DECLARE v_def TEXT;
        BEGIN
            SELECT pg_get_constraintdef(oid) INTO v_def
            FROM pg_constraint
            WHERE conrelid = '{_TABLE_NAME}'::regclass
              AND conname  = '{_CONSTRAINT_NAME}';

            IF v_def IS NULL THEN
                RAISE NOTICE 'Contrainte % absente — skip', '{_CONSTRAINT_NAME}';
                RETURN;
            END IF;

            IF v_def LIKE '%review_opened%' THEN
                RAISE NOTICE 'review_opened déjà présent — idempotent skip';
                RETURN;
            END IF;

            EXECUTE $q$ALTER TABLE {_TABLE_NAME} DROP CONSTRAINT {_CONSTRAINT_NAME}$q$;
            RAISE NOTICE 'Contrainte % supprimée', '{_CONSTRAINT_NAME}';

            EXECUTE $q$ALTER TABLE {_TABLE_NAME}
                ADD CONSTRAINT {_CONSTRAINT_NAME}
                CHECK (event_type = ANY ({new_array}))$q$;
            RAISE NOTICE 'Contrainte % recréée avec review_opened', '{_CONSTRAINT_NAME}';
        END $$;
    """)


def downgrade() -> None:
    old_array = _build_array_literal(_VALID_EVENT_TYPES_OLD)
    op.execute(f"""
        DO $$
        DECLARE v_def TEXT;
        BEGIN
            SELECT pg_get_constraintdef(oid) INTO v_def
            FROM pg_constraint
            WHERE conrelid = '{_TABLE_NAME}'::regclass
              AND conname  = '{_CONSTRAINT_NAME}';

            IF v_def IS NULL THEN
                RAISE NOTICE 'Contrainte % absente — skip downgrade', '{_CONSTRAINT_NAME}';
                RETURN;
            END IF;

            IF v_def LIKE '%recommendation_set%' THEN
                RAISE NOTICE 'recommendation_set déjà présent — downgrade déjà appliqué';
                RETURN;
            END IF;

            EXECUTE $q$ALTER TABLE {_TABLE_NAME} DROP CONSTRAINT {_CONSTRAINT_NAME}$q$;

            EXECUTE $q$ALTER TABLE {_TABLE_NAME}
                ADD CONSTRAINT {_CONSTRAINT_NAME}
                CHECK (event_type = ANY ({old_array}))$q$;
            RAISE NOTICE 'DOWNGRADE : contrainte % restaurée avec recommendation_set', '{_CONSTRAINT_NAME}';
        END $$;
    """)
