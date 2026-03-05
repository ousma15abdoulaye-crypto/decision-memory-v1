"""
scripts/build_dictionary.py

M6 Dictionary Build · Enrichissement couche_b depuis mercurials + imc.
Source de vérité : couche_b.procurement_dict_*.
psycopg v3 synchrone · RÈGLE-39.
RETURNING item_id sur INSERT → zéro alias orphelin.
dry-run = lecture seule garantie · RÈGLE-42.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/build_dictionary.py --dry-run
    python scripts/build_dictionary.py --dry-run --min-freq 3
    python scripts/build_dictionary.py --min-freq 2
    python scripts/build_dictionary.py --min-freq 2 --activate
"""

from __future__ import annotations
import argparse
import json
import logging
import math
import os
import sys
import uuid as _uuid
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.couche_b.dictionary.normalizer import (
    normalize_label,
    build_canonical_slug,
    generate_deterministic_id,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL manquante · $env:DATABASE_URL = '<valeur>'")
    sys.exit(1)

# psycopg attend postgresql:// pas postgresql+psycopg://
if "postgresql+psycopg://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")


# ============================================================
# STRUCTURES
# ============================================================

@dataclass
class RawItem:
    raw:        str
    normalized: str
    slug:       str
    freq:       int        = 0
    sources:    list[str]  = field(default_factory=list)
    zones:      set[str]   = field(default_factory=set)
    imc_anchor: bool       = False


@dataclass
class SchemaState:
    """Colonnes réelles · lues depuis DB · RÈGLE-40."""
    collision_cols: set[str] = field(default_factory=set)
    proposals_cols: set[str] = field(default_factory=set)
    existing_slugs: set[str] = field(default_factory=set)


@dataclass
class BuildReport:
    total_raw:        int       = 0
    total_normalized: int       = 0
    new_items:        int       = 0
    updated_items:    int       = 0
    new_aliases:      int       = 0
    review_queue:     int       = 0
    collisions:       int       = 0
    skipped:          int       = 0
    errors:           list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "=" * 65,
            "RAPPORT BUILD DICTIONARY M6",
            "=" * 65,
            f"  Libellés bruts           : {self.total_raw}",
            f"  Formes normalisées       : {self.total_normalized}",
            f"  Nouveaux items           : {self.new_items}",
            f"  Items mis à jour         : {self.updated_items}",
            f"  Nouveaux aliases         : {self.new_aliases}",
            f"  File validation humaine  : {self.review_queue}",
            f"  Collisions loggées       : {self.collisions}",
            f"  Skippés (freq basse)     : {self.skipped}",
            f"  Erreurs                  : {len(self.errors)}",
        ]
        if self.errors:
            lines.append("\n  ERREURS :")
            for e in self.errors[:10]:
                lines.append(f"    · {e}")
        lines.append("=" * 65)
        return "\n".join(lines)


# ============================================================
# VÉRIFICATIONS PRÉALABLES
# ============================================================

def assert_prerequisites(conn: psycopg.Connection) -> None:
    """
    Vérifie que M6 a tourné et que couche_b est intacte.
    Fail-loud si prérequis manquants.
    """
    row = conn.execute("""
        SELECT COUNT(*) AS n
        FROM information_schema.columns
        WHERE table_schema = 'couche_b'
          AND table_name   = 'procurement_dict_items'
          AND column_name  = 'canonical_slug'
    """).fetchone()

    if not row or row["n"] == 0:
        raise RuntimeError(
            "canonical_slug absent de couche_b.procurement_dict_items\n"
            "Migration m6_dictionary_build requise d'abord."
        )

    row = conn.execute("""
        SELECT COUNT(*) AS n
        FROM couche_b.procurement_dict_items
    """).fetchone()

    if not row or row["n"] < 51:
        raise RuntimeError(
            f"procurement_dict_items : {row['n'] if row else 0} lignes"
            f" · attendu ≥ 51"
        )


def load_schema_state(conn: psycopg.Connection) -> SchemaState:
    """Lit l'état réel du schéma pour les INSERTs · RÈGLE-40."""
    ss = SchemaState()

    rows = conn.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'dict_collision_log'
    """).fetchall()
    ss.collision_cols = {r["column_name"] for r in rows}

    rows = conn.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'couche_b'
          AND table_name   = 'dict_proposals'
    """).fetchall()
    ss.proposals_cols = {r["column_name"] for r in rows}

    rows = conn.execute("""
        SELECT canonical_slug FROM couche_b.procurement_dict_items
        WHERE canonical_slug IS NOT NULL
    """).fetchall()
    ss.existing_slugs = {r["canonical_slug"] for r in rows}

    return ss


# ============================================================
# EXTRACTION
# ============================================================

def extract_raw_items(conn: psycopg.Connection) -> list[RawItem]:
    """
    Extrait libellés bruts depuis mercurials + imc_entries.
    Fréquence · zones · ancrage IMC.
    mercurials.item_canonical · imc_entries.category_raw
    """
    items: dict[str, RawItem] = {}

    rows = conn.execute("""
        SELECT
            item_canonical,
            COUNT(*)                    AS freq,
            ARRAY_AGG(DISTINCT zone_id) AS zones
        FROM mercurials
        WHERE item_canonical IS NOT NULL
          AND TRIM(item_canonical) != ''
        GROUP BY item_canonical
        ORDER BY freq DESC
    """).fetchall()

    for row in rows:
        raw  = row["item_canonical"]
        slug = build_canonical_slug(raw)
        if not slug:
            continue
        if slug not in items:
            items[slug] = RawItem(
                raw=raw,
                normalized=normalize_label(raw),
                slug=slug,
            )
        items[slug].freq += row["freq"]
        items[slug].sources.append("mercuriale")
        items[slug].zones.update(
            z for z in (row["zones"] or []) if z
        )

    rows = conn.execute("""
        SELECT DISTINCT category_raw
        FROM imc_entries
        WHERE category_raw IS NOT NULL
          AND TRIM(category_raw) != ''
    """).fetchall()

    for row in rows:
        raw  = row["category_raw"]
        slug = build_canonical_slug(raw)
        if not slug:
            continue
        if slug not in items:
            items[slug] = RawItem(
                raw=raw,
                normalized=normalize_label(raw),
                slug=slug,
            )
        items[slug].sources.append("imc")
        items[slug].imc_anchor = True

    return list(items.values())


# ============================================================
# SCORING
# ============================================================

def compute_confidence(item: RawItem) -> float:
    score = 0.0
    if item.freq > 0:
        score += min(math.log10(item.freq + 1) / 4.0, 0.45)
    score += min(len(item.zones) * 0.05, 0.20)
    if item.imc_anchor:
        score += 0.25
    if len(set(item.sources)) >= 2:
        score += 0.10
    return round(min(score, 1.0), 4)


# ============================================================
# LOG COLLISION · RÈGLE-37 · RÈGLE-40
# ============================================================

def log_collision(
    conn: psycopg.Connection,
    ss: SchemaState,
    item_a_id: str,
    item_b_id: str,
    alias_conflicted: str,
) -> None:
    """
    Log collision dans dict_collision_log.
    INSERT construit sur colonnes réelles uniquement · RÈGLE-40.
    Jamais de résolution auto · RÈGLE-37.
    resolution = 'unresolved' (CHECK 036)
    """
    wanted: dict = {
        "id":               str(_uuid.uuid4()),
        "raw_text_1":       item_a_id,
        "raw_text_2":       item_b_id,
        "fuzzy_score":      0.0,
        "category_match":   False,
        "unit_match":       False,
        "resolution":       "unresolved",
        "resolved_by":      "system",
        "collision_type":   "synonym_conflict",
        "item_a_id":        item_a_id,
        "item_b_id":        item_b_id,
        "alias_conflicted": alias_conflicted,
    }

    present = {
        k: v for k, v in wanted.items()
        if k in ss.collision_cols
    }

    if "id" not in present or len(present) < 3:
        logger.warning(
            "dict_collision_log colonnes insuffisantes · skippé"
        )
        return

    cols   = list(present.keys())
    values = list(present.values())

    try:
        conn.execute(
            f"INSERT INTO dict_collision_log "
            f"({', '.join(cols)}) "
            f"VALUES ({', '.join(['%s'] * len(cols))})",
            values,
        )
    except Exception as exc:
        logger.error("log_collision KO : %s", exc)


# ============================================================
# LOG PROPOSAL · RÈGLE-25 · RÈGLE-40
# ============================================================

def log_proposal(
    conn: psycopg.Connection,
    ss: SchemaState,
    item_id: str,
    raw: str,
    confidence: float,
) -> None:
    """
    Log dans couche_b.dict_proposals.
    Colonnes réelles uniquement · RÈGLE-40.
    human_validated = FALSE · RÈGLE-25.
    """
    wanted = {
        "id":            generate_deterministic_id(
            f"dp_{item_id}_{raw}", prefix="dp"
        ),
        "item_id":       item_id,
        "proposed_form": raw,
        "confidence":    confidence,
        "status":        "pending",
    }

    present = {
        k: v for k, v in wanted.items()
        if k in ss.proposals_cols
    }

    if "id" not in present or "item_id" not in present:
        return

    cols   = list(present.keys())
    values = list(present.values())

    try:
        conn.execute(
            f"INSERT INTO couche_b.dict_proposals "
            f"({', '.join(cols)}) "
            f"VALUES ({', '.join(['%s'] * len(cols))}) "
            f"ON CONFLICT (id) DO NOTHING",
            values,
        )
    except Exception as exc:
        logger.error("log_proposal KO : %s", exc)


# ============================================================
# INSERTION ITEM
# ============================================================

def insert_item(
    conn: psycopg.Connection,
    ss: SchemaState,
    item: RawItem,
    confidence: float,
    min_freq: int,
    report: BuildReport,
) -> None:
    """
    Insère ou met à jour dans couche_b.procurement_dict_items.
    Si slug existe déjà (51 items seed) → mise à jour sources + alias.
    RETURNING item_id → zéro alias orphelin.
    """
    if item.freq < min_freq and not item.imc_anchor:
        report.skipped += 1
        return

    is_new_slug = item.slug not in ss.existing_slugs

    try:
        if is_new_slug:
            item_id = item.slug
            conn.execute(
                """
                INSERT INTO couche_b.procurement_dict_items (
                    item_id, family_id, label_fr,
                    default_unit, active,
                    canonical_slug, dict_version,
                    confidence_score, human_validated,
                    sources, last_seen
                ) VALUES (
                    %s, 'equipements', %s,
                    'unite', TRUE,
                    %s, '1.0.0',
                    %s, FALSE,
                    %s, CURRENT_DATE
                )
                ON CONFLICT (item_id) DO UPDATE
                    SET confidence_score = GREATEST(
                            couche_b.procurement_dict_items.confidence_score,
                            EXCLUDED.confidence_score
                        ),
                        sources   = EXCLUDED.sources,
                        last_seen = CURRENT_DATE,
                        updated_at = NOW()
                """,
                (
                    item_id, item.raw,
                    item.slug,
                    confidence,
                    json.dumps(sorted(set(item.sources))),
                ),
            )
            report.new_items += 1
            ss.existing_slugs.add(item.slug)
        else:
            item_id = item.slug
            conn.execute(
                """
                UPDATE couche_b.procurement_dict_items
                SET sources   = CASE
                    WHEN sources @> %s::jsonb THEN sources
                    ELSE sources || %s::jsonb
                END,
                last_seen  = CURRENT_DATE,
                updated_at = NOW()
                WHERE item_id = %s
                """,
                (
                    json.dumps(sorted(set(item.sources))),
                    json.dumps(sorted(set(item.sources))),
                    item_id,
                ),
            )
            report.updated_items += 1

        # Détection collision alias
        existing_alias = conn.execute(
            """
            SELECT item_id FROM couche_b.procurement_dict_aliases
            WHERE normalized_alias = %s
              AND item_id != %s
            LIMIT 1
            """,
            (item.normalized, item_id),
        ).fetchone()

        if existing_alias:
            report.collisions += 1
            log_collision(
                conn, ss,
                existing_alias["item_id"],
                item_id,
                item.normalized,
            )
            if confidence < 0.75:
                log_proposal(conn, ss, item_id, item.raw, confidence)
                report.review_queue += 1
            return

        # Insérer alias
        conn.execute(
            """
            INSERT INTO couche_b.procurement_dict_aliases (
                item_id, alias_raw, normalized_alias, source
            ) VALUES (%s, %s, %s, %s)
            ON CONFLICT (normalized_alias) DO NOTHING
            """,
            (
                item_id, item.raw, item.normalized,
                item.sources[0] if item.sources else "mercuriale",
            ),
        )
        report.new_aliases += 1

        if confidence < 0.75:
            log_proposal(conn, ss, item_id, item.raw, confidence)
            report.review_queue += 1

    except Exception as exc:
        logger.error(
            "Erreur '%s' (slug=%s) : %s",
            item.raw, item.slug, exc,
        )
        report.errors.append(f"{item.slug}: {exc}")


# ============================================================
# POINT D'ENTRÉE
# ============================================================

def main(dry_run: bool, min_freq: int) -> None:

    mode = "DRY-RUN · LECTURE SEULE" if dry_run else "IMPORT RÉEL"
    logger.info("=" * 65)
    logger.info("BUILD DICTIONARY M6 — %s · min_freq=%d", mode, min_freq)
    logger.info("=" * 65)

    report = BuildReport()

    if dry_run:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            assert_prerequisites(conn)
            ss    = load_schema_state(conn)
            items = extract_raw_items(conn)
            report.total_raw = len(items)

            slugs_seen: set[str] = set()
            for item in items:
                report.total_normalized += 1
                if item.slug in slugs_seen:
                    logger.warning(
                        "Slug dupliqué '%s' ← '%s'",
                        item.slug, item.raw,
                    )
                slugs_seen.add(item.slug)

                if item.freq < min_freq and not item.imc_anchor:
                    report.skipped += 1
                    continue

                confidence = compute_confidence(item)
                if item.slug in ss.existing_slugs:
                    report.updated_items += 1
                else:
                    report.new_items   += 1
                    report.new_aliases += 1

                if confidence < 0.75:
                    report.review_queue += 1

        print(report.summary())
        logger.info("DRY-RUN terminé · zéro écriture · connexion fermée")
        return

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        assert_prerequisites(conn)
        ss = load_schema_state(conn)

        logger.info(
            "Schema collision_log : %d colonnes",
            len(ss.collision_cols),
        )
        logger.info(
            "Schema proposals     : %d colonnes",
            len(ss.proposals_cols),
        )
        logger.info(
            "Items seed existants : %d",
            len(ss.existing_slugs),
        )

        with conn.transaction():
            items = extract_raw_items(conn)
            report.total_raw = len(items)
            logger.info("%d libellés bruts extraits", report.total_raw)

            slugs_seen: set[str] = set()
            for item in items:
                report.total_normalized += 1
                if item.slug in slugs_seen:
                    logger.warning(
                        "Slug dupliqué '%s' ← '%s'",
                        item.slug, item.raw,
                    )
                slugs_seen.add(item.slug)

                confidence = compute_confidence(item)
                insert_item(
                    conn, ss, item,
                    confidence, min_freq, report,
                )

    print(report.summary())

    if report.collisions > 0:
        logger.warning(
            "%d collisions → dict_collision_log · RÈGLE-37",
            report.collisions,
        )
    if report.review_queue > 0:
        logger.warning(
            "%d items → dict_proposals pending · RÈGLE-25",
            report.review_queue,
        )
    if report.errors:
        logger.error("%d erreurs", len(report.errors))
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build dictionnaire procurement DMS M6"
    )
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--min-freq", type=int, default=2)
    args = parser.parse_args()
    main(args.dry_run, args.min_freq)
