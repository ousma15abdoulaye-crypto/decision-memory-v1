"""m5_geo_patch_koutiala

Ajoute les zones Mali manquantes identifiées lors du dry-run M5 :
  - Koutiala (cercle, Sikasso) — zone la plus active dans la mercuriale 2024
  - Kadiolo, Yorosso (autres cercles Sikasso présents dans la mercuriale)
  - Kolondièba (cercle Sikasso)

Problème détecté : dry-run 2026-03-04 · des centaines de WARNING
  "Zone non résolue : 'Koutiala' → 0 résultat · zone_id = NULL"
  car Koutiala absent de la migration m5_geo_fix_master.

Décisions :
  - INSERT idempotent ON CONFLICT (id) DO UPDATE
  - Zones préservées telles quelles si déjà présentes

Révision     : m5_geo_patch_koutiala
Down revision: 040_mercuriale_ingest
"""

revision = "m5_geo_patch_koutiala"
down_revision = "040_mercuriale_ingest"
branch_labels = None
depends_on = None

from alembic import op

# Zones manquantes identifiées lors du dry-run M5
# (id stable · name · level · type · parent_id)
_NEW_ZONES = [
    ("zone-koutiala-1",    "Koutiala",    2, "cercle", "zone-sikasso-1"),
    ("zone-kadiolo-1",     "Kadiolo",     2, "cercle", "zone-sikasso-1"),
    ("zone-yorosso-1",     "Yorosso",     2, "cercle", "zone-sikasso-1"),
    ("zone-kolondieba-1",  "Kolondièba",  2, "cercle", "zone-sikasso-1"),
    # Autres cercles fréquents dans les mercuriales Mali
    ("zone-bla-1",         "Bla",         2, "cercle", "zone-segou-1"),
    ("zone-macina-1",      "Macina",      2, "cercle", "zone-segou-1"),
    ("zone-baroueli-1",    "Baraouéli",   2, "cercle", "zone-segou-1"),
    ("zone-tenenkou-1",    "Ténenkou",    2, "cercle", "zone-mopti-1"),
    ("zone-koro-1",        "Koro",        2, "cercle", "zone-mopti-1"),
    ("zone-bandiagara-1",  "Bandiagara",  2, "cercle", "zone-mopti-1"),
    ("zone-douentza-1",    "Douentza",    2, "cercle", "zone-mopti-1"),
    ("zone-bankass-1",     "Bankass",     2, "cercle", "zone-mopti-1"),
    ("zone-djenne-1",      "Djenné",      2, "cercle", "zone-mopti-1"),
]


def upgrade() -> None:
    for geo_id, name, level, geo_type, parent_id in _NEW_ZONES:
        safe_name = name.replace("'", "''")
        op.execute(f"""
            INSERT INTO geo_master (id, name, level, type, parent_id, created_at)
            VALUES (
                '{geo_id}', '{safe_name}', {level}, '{geo_type}', '{parent_id}',
                now()
            )
            ON CONFLICT (id) DO UPDATE
                SET name      = EXCLUDED.name,
                    level     = EXCLUDED.level,
                    type      = EXCLUDED.type,
                    parent_id = EXCLUDED.parent_id;
        """)

    op.execute("""
        DO $$
        DECLARE v_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO v_count FROM geo_master;
            RAISE NOTICE 'm5_geo_patch_koutiala · geo_master : % zones au total', v_count;
        END $$;
    """)


def downgrade() -> None:
    ids = ", ".join(f"'{geo_id}'" for geo_id, *_ in _NEW_ZONES)
    op.execute(f"DELETE FROM geo_master WHERE id IN ({ids});")
