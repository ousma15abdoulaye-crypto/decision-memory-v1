"""
Probe pré-M7.4 · RÈGLE-08.
Vérifie TOUS les prérequis avant toute écriture.
Auto-exit si STOP signal détecté.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/probe_m74.py
"""
from __future__ import annotations

import math
import os
import sys

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("❌ DATABASE_URL manquante")
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


SEED_ATTENDU   = 51
BATCH_SIZE     = 10
TOKENS_IN      = 600 * BATCH_SIZE
TOKENS_OUT     = 150 * BATCH_SIZE
COST_IN        = float(os.environ.get("M7_COST_IN",  "0.2"))
COST_OUT       = float(os.environ.get("M7_COST_OUT", "0.6"))
MAX_COST_SYNC  = 10.0

# Triggers requis depuis M7.3b (noms exacts)
REQUIRED_TRIGGERS = {
    "trg_block_legacy_family_insert",
    "trg_block_legacy_family_update",
}


def run() -> None:
    print("=" * 70)
    print("PROBE P0→P9 — M7.4 DICT VIVANT · PRÉ-MIGRATION")
    print("=" * 70)
    stops: list[str] = []

    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:

        # P0 · Triggers existants (noms réels depuis DB · pas hardcodés)
        print("\n--- P0_TRIGGERS_EXISTANTS ---")
        rows = conn.execute("""
            SELECT trigger_name, action_timing, event_manipulation
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
            ORDER BY trigger_name
        """).fetchall()
        existing_triggers = {r["trigger_name"] for r in rows}
        print(f"  Triggers actifs ({len(rows)}) :")
        for r in rows:
            print(f"    {r['trigger_name']:<50} "
                  f"{r['action_timing']} {r['event_manipulation']}")

        for trig in REQUIRED_TRIGGERS:
            if trig not in existing_triggers:
                stops.append(f"STOP-PRE: {trig} absent")
                print(f"  ⛔ REQUIS ABSENT : {trig}")

        # P0b · Guard pg_trigger_depth dans fn_compute_quality_score
        print("\n--- P0B_TRIGGER_GUARD ---")
        r = conn.execute("""
            SELECT prosrc FROM pg_proc
            WHERE proname = 'fn_compute_quality_score'
              AND pronamespace = (
                SELECT oid FROM pg_namespace WHERE nspname = 'couche_b'
              )
        """).fetchone()
        if r:
            has_guard = "pg_trigger_depth" in r["prosrc"]
            has_subquery = "SELECT EXISTS" in r["prosrc"] or \
                           "dict_price_references" in r["prosrc"]
            print(f"  pg_trigger_depth guard : {'OK' if has_guard else 'ABSENT'}")
            print(f"  Sous-requête interne   : "
                  f"{'⚠ PRÉSENTE → RÈGLE-QS violée' if has_subquery else 'OK · O(1)'}")
            if not has_guard:
                stops.append("STOP-TRG: pg_trigger_depth absent")
            if has_subquery:
                stops.append(
                    "STOP-TRG: trigger quality_score contient sous-requête "
                    "→ RÈGLE-QS violée · migration M7.4 la corrige"
                )
        else:
            print("  fn_compute_quality_score : absente → créée par migration")

        # P1 · HEAD Alembic
        print("\n--- P1_ALEMBIC_HEAD ---")
        r = conn.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        print(f"  HEAD actuel (down_revision M7.4) : {r['version_num']}")

        # P2 · État classification
        print("\n--- P2_CLASSIFICATION ---")
        r = conn.execute("""
            SELECT
                COUNT(*)                                          AS total,
                COUNT(*) FILTER (WHERE domain_id IS NULL)         AS sans_domaine,
                COUNT(*) FILTER (WHERE domain_id IS NOT NULL)     AS avec_domaine,
                COUNT(*) FILTER (WHERE human_validated = TRUE)    AS seed,
                COUNT(*) FILTER (
                    WHERE LENGTH(TRIM(COALESCE(label_fr,''))) <= 5
                ) AS label_court
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
        """).fetchone()
        print(f"  Total actifs     : {r['total']}")
        print(f"  Avec domain_id   : {r['avec_domaine']}")
        print(f"  Sans domain_id   : {r['sans_domaine']} ← à classifier")
        print(f"  Seed protégés    : {r['seed']}")
        print(f"  Labels courts    : {r['label_court']} ← exclus LLM")

        if r["seed"] != SEED_ATTENDU:
            stops.append(f"STOP-V5: seed {r['seed']} ≠ {SEED_ATTENDU}")
        if r["avec_domaine"] > r["total"] * 0.8:
            stops.append("STOP-V1: >80% items déjà classifiés")

        # P3 · Taxonomie EN BASE (DA-TAXO-DB)
        print("\n--- P3_TAXO_EN_BASE ---")
        for table, min_expected in [
            ("taxo_l1_domains",    15),
            ("taxo_l2_families",   40),
            ("taxo_l3_subfamilies", 50),
        ]:
            r = conn.execute(
                f"SELECT COUNT(*) AS n FROM couche_b.{table}"
            ).fetchone()
            status = "OK" if r["n"] >= min_expected else f"⚠ {r['n']} < {min_expected}"
            print(f"  {table:<30} {r['n']:>4} {status}")
            if r["n"] < min_expected:
                stops.append(
                    f"STOP-DB: {table} trop vide ({r['n']} < {min_expected}) "
                    f"→ lancer scripts/seed_taxonomy_v2.py avant Phase A"
                )

        # P4 · taxo_proposals_v2 état
        print("\n--- P4_PROPOSALS ---")
        rows = conn.execute("""
            SELECT status, COUNT(*) AS n
            FROM couche_b.taxo_proposals_v2
            GROUP BY status ORDER BY n DESC
        """).fetchall()
        print("  (vide)" if not rows else "")
        for row in rows:
            print(f"  {row['status']:<20} {row['n']}")

        # P5 · Bug backfill résiduel
        print("\n--- P5_BUG_BACKFILL ---")
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM couche_b.taxo_proposals_v2 p
            JOIN couche_b.procurement_dict_items i USING (item_id)
            WHERE p.status = 'approved'
              AND i.domain_id IS NULL
              AND i.human_validated = FALSE
        """).fetchone()
        print(f"  Approved sans domain_id (backfill manquant) : {r['n']}")
        if r["n"] > 0:
            print("  → fix_backfill_taxonomy.py requis avant Phase A")

        # P6 · Colonnes approved_by/approved_at sur taxo_proposals_v2
        print("\n--- P6_COLONNES_AUDIT ---")
        for col in ["approved_by", "approved_at", "reviewed_by",
                    "token_entropy", "confidence_source",
                    "calibrated_confidence", "batch_job_id"]:
            r = conn.execute("""
                SELECT COUNT(*) AS n FROM information_schema.columns
                WHERE table_schema = 'couche_b'
                  AND table_name   = 'taxo_proposals_v2'
                  AND column_name  = %s
            """, (col,)).fetchone()
            print(f"  {col:<30} {'EXISTE' if r['n'] > 0 else 'ABSENT → migration'}")

        # P7 · quality_score et updated_at sur dict_items
        print("\n--- P7_COLONNES_DICT_ITEMS ---")
        for col in ["quality_score", "updated_at", "domain_id",
                    "family_l2_id", "subfamily_id",
                    "classification_confidence", "classification_source"]:
            r = conn.execute("""
                SELECT COUNT(*) AS n FROM information_schema.columns
                WHERE table_schema = 'couche_b'
                  AND table_name   = 'procurement_dict_items'
                  AND column_name  = %s
            """, (col,)).fetchone()
            print(f"  {col:<35} {'EXISTE' if r['n'] > 0 else 'ABSENT → migration'}")

        # P8 · Estimation coût
        print("\n--- P8_ESTIMATION_COUT ---")
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
              AND domain_id IS NULL
              AND label_fr IS NOT NULL
              AND LENGTH(TRIM(label_fr)) > 5
              AND COALESCE(canonical_slug, '') !~ '^[0-9]+$'
        """).fetchone()
        n_items    = r["n"]
        n_calls    = math.ceil(n_items / BATCH_SIZE)
        cost_sync  = n_calls * (
            TOKENS_IN * COST_IN / 1_000_000
            + TOKENS_OUT * COST_OUT / 1_000_000
        )
        cost_batch = cost_sync * 0.5
        print(f"  Items à classifier   : {n_items}")
        print(f"  Coût estimé SYNC     : ${cost_sync:.4f} USD")
        print(f"  Coût estimé BATCH    : ${cost_batch:.4f} USD (−50%)")
        if cost_sync > MAX_COST_SYNC:
            stops.append(
                f"STOP-V2: SYNC ${cost_sync:.2f} > ${MAX_COST_SYNC} "
                f"· recommander --mode batch (${cost_batch:.2f})"
            )

        # P9 · Variables d'environnement
        print("\n--- P9_ENV_VARS ---")
        for var in ["DATABASE_URL", "DMS_MISTRAL", "DMSMISTRALAPI",
                    "MISTRAL_API_KEY", "M7_COST_IN", "M7_COST_OUT"]:
            val = os.environ.get(var)
            print(f"  {var:<25} {'SET' if val else 'ABSENT'}")
        if not (os.environ.get("DMS_MISTRAL") or
                os.environ.get("DMSMISTRALAPI") or
                os.environ.get("MISTRAL_API_KEY")):
            stops.append(
                "STOP: DMS_MISTRAL ou DMSMISTRALAPI ou MISTRAL_API_KEY manquante"
            )

    print("\n" + "=" * 70)
    if stops:
        print("⛔ STOP SIGNALS DÉTECTÉS :")
        for s in stops:
            print(f"  {s}")
        print("\nNE PAS CONTINUER.")
        print("POSTER P0→P9 COMPLETS. ATTENDRE GO TECH LEAD.")
        sys.exit(1)
    else:
        print("✅ PROBE OK — POSTER P0→P9 — ATTENDRE GO TECH LEAD")
    print("=" * 70)


if __name__ == "__main__":
    run()
