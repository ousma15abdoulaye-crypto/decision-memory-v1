"""
m5_geo_fix_master

Enrichit geo_master avec les 16 zones mercuriales Mali 2023.

Problème identifié (probe M5 · 2026-03-04) :
  geo_master contient 3 enregistrements (Bamako · Kayes · Sikasso)
  avec type='city' (sans colonne level).
  Les mercuriales 2023 couvrent 16 zones.
  Sans cet enrichissement : zone_id = NULL pour 13/16 zones.

Décisions :
  - Ajoute colonne 'level' INTEGER si absente (1=région · 2=cercle · 3=commune)
  - Conserve 'type' VARCHAR pour compat existante
  - Met à jour les 3 existants (type city → region · level = 1)
  - INSERT idempotent ON CONFLICT (id) DO UPDATE
  - Les ids stables préfixe zone- garantissent idempotence

Révision     : m5_geo_fix_master
Down revision: m5_cleanup_a_committee_event_type_check
"""

revision = "m5_geo_fix_master"
down_revision = "m5_cleanup_a_committee_event_type_check"
branch_labels = None
depends_on = None

from alembic import op

# 16 zones mercuriales Mali
# (id · name · level · type · parent_id)
GEO_ZONES = [
    ("zone-bamako-1",     "Bamako",     1, "region", None),
    ("zone-kayes-1",      "Kayes",      1, "region", None),
    ("zone-sikasso-1",    "Sikasso",    1, "region", None),
    ("zone-koulikoro-1",  "Koulikoro",  1, "region", None),
    ("zone-segou-1",      "Ségou",      1, "region", None),
    ("zone-mopti-1",      "Mopti",      1, "region", None),
    ("zone-tombouctou-1", "Tombouctou", 1, "region", None),
    ("zone-gao-1",        "Gao",        1, "region", None),
    ("zone-kidal-1",      "Kidal",      1, "region", None),
    ("zone-taoudeni-1",   "Taoudeni",   1, "region", None),
    ("zone-menaka-1",     "Ménaka",     1, "region", None),
    ("zone-bougouni-1",   "Bougouni",   2, "cercle", "zone-sikasso-1"),
    ("zone-dioila-1",     "Dioïla",     2, "cercle", "zone-koulikoro-1"),
    ("zone-kita-1",       "Kita",       2, "cercle", "zone-kayes-1"),
    ("zone-nara-1",       "Nara",       2, "cercle", "zone-koulikoro-1"),
    ("zone-nioro-1",      "Nioro",      2, "cercle", "zone-kayes-1"),
    ("zone-san-1",        "San",        2, "cercle", "zone-segou-1"),
]


def upgrade() -> None:

    # ── Garde idempotence : ajouter colonne level si absente ─────────────
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name  = 'geo_master'
                  AND column_name = 'level'
            ) THEN
                ALTER TABLE geo_master ADD COLUMN level INTEGER;
                RAISE NOTICE 'Colonne level ajoutée à geo_master';
            ELSE
                RAISE NOTICE 'Colonne level déjà présente — skip ALTER';
            END IF;
        END $$;
    """)

    # ── Mettre à jour les 3 enregistrements existants (city → region) ────
    op.execute("""
        UPDATE geo_master
        SET level = 1,
            type  = 'region'
        WHERE name IN ('Bamako', 'Kayes', 'Sikasso')
          AND (level IS NULL OR type = 'city');
    """)

    # ── INSERT idempotent des 16 zones ───────────────────────────────────
    for geo_id, name, level, geo_type, parent_id in GEO_ZONES:
        parent_val = f"'{parent_id}'" if parent_id else "NULL"
        # Échappement apostrophes dans les noms (Dioïla, Ménaka…)
        name_escaped = name.replace("'", "''")
        op.execute(f"""
            INSERT INTO geo_master (id, name, level, type, parent_id, created_at)
            VALUES (
                '{geo_id}',
                '{name_escaped}',
                {level},
                '{geo_type}',
                {parent_val},
                now()::text
            )
            ON CONFLICT (id) DO UPDATE
                SET level     = EXCLUDED.level,
                    type      = EXCLUDED.type,
                    parent_id = EXCLUDED.parent_id;
        """)

    op.execute("""
        DO $$
        DECLARE v_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO v_count FROM geo_master;
            RAISE NOTICE 'M5-GEO-FIX · geo_master : % enregistrements', v_count;
        END $$;
    """)


def downgrade() -> None:
    # Supprimer les 14 zones ajoutées par cette migration
    # Préserver les 3 originales (Bamako · Kayes · Sikasso)
    op.execute("""
        DELETE FROM geo_master
        WHERE id IN (
            'zone-koulikoro-1', 'zone-segou-1',   'zone-mopti-1',
            'zone-tombouctou-1','zone-gao-1',      'zone-kidal-1',
            'zone-taoudeni-1',  'zone-menaka-1',   'zone-bougouni-1',
            'zone-dioila-1',    'zone-kita-1',     'zone-nara-1',
            'zone-nioro-1',     'zone-san-1'
        );
    """)
    # Restaurer type='city' et level=NULL pour les 3 originales
    op.execute("""
        UPDATE geo_master
        SET type  = 'city',
            level = NULL
        WHERE id IN ('zone-bamako-1', 'zone-kayes-1', 'zone-sikasso-1');
    """)
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE 'DOWNGRADE m5_geo_fix_master · 14 zones supprimées · 3 originales restaurées';
        END $$;
    """)
