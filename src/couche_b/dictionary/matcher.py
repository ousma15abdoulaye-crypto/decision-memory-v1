"""
src/couche_b/dictionary/matcher.py

Point d'entrée unique matching procurement · RÈGLE-36.
M9 · M11 · M14 = match_item() uniquement.
Lit depuis couche_b directement (source de vérité).
psycopg v3 synchrone · RÈGLE-39.

Niveaux :
  1. EXACT      normalized_alias = normalize_label(input)
  2. NORMALIZED canonical_slug   = normalize_label(input)
  3. TRIGRAM    pg_trgm ≥ 0.82 sur normalized_alias
  4. UNRESOLVED jamais silencieux · review_required = True
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import psycopg
from psycopg.rows import dict_row

from .normalizer import normalize_label

logger = logging.getLogger(__name__)

TRIGRAM_THRESHOLD: float = 0.82


class MatchMethod(str, Enum):
    EXACT      = "exact"
    NORMALIZED = "normalized"
    TRIGRAM    = "trigram"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class MatchResult:
    """
    Immuable · hashable.
    RÈGLE-19 : confidence + evidence sur chaque résolution.
    """
    item_id:         Optional[str]
    canonical_form:  Optional[str]
    unit_canonical:  Optional[str]
    family_id:       Optional[str]
    confidence:      float
    match_method:    MatchMethod
    requires_review: bool
    evidence:        Optional[str]

    def to_dict(self) -> dict:
        return {
            "item_id":         self.item_id,
            "canonical_form":  self.canonical_form,
            "unit_canonical":  self.unit_canonical,
            "family_id":       self.family_id,
            "confidence":      self.confidence,
            "match_method":   self.match_method.value,
            "requires_review": self.requires_review,
            "evidence":       self.evidence,
        }


_UNRESOLVED = MatchResult(
    item_id=None, canonical_form=None,
    unit_canonical=None, family_id=None,
    confidence=0.0, match_method=MatchMethod.UNRESOLVED,
    requires_review=True, evidence=None,
)


def _trgm_available(conn: psycopg.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
    ).fetchone()
    return row is not None


def match_item(
    conn: psycopg.Connection,
    raw_label: str,
) -> MatchResult:
    """
    Matching synchrone · 3 niveaux · dégradation gracieuse.
    Source de vérité : couche_b.procurement_dict_*.
    Jamais silencieux sur UNRESOLVED.
    """
    if not raw_label or not raw_label.strip():
        logger.warning("match_item · label vide")
        return _UNRESOLVED

    normalized = normalize_label(raw_label)
    if not normalized:
        return _UNRESOLVED

    # ----------------------------------------------------------
    # NIVEAU 1 · Exact sur normalized_alias
    # Colonne existante · UNIQUE · index btree
    # ----------------------------------------------------------
    row = conn.execute(
        """
        SELECT
            i.item_id,
            i.label_fr          AS canonical_form,
            i.default_unit      AS unit_canonical,
            i.family_id,
            i.confidence_score,
            a.normalized_alias  AS evidence
        FROM couche_b.procurement_dict_aliases a
        JOIN couche_b.procurement_dict_items i
            ON i.item_id = a.item_id
        WHERE a.normalized_alias = %s
          AND i.active = TRUE
        LIMIT 1
        """,
        (normalized,),
    ).fetchone()

    if row:
        return MatchResult(
            item_id=row["item_id"],
            canonical_form=row["canonical_form"],
            unit_canonical=row["unit_canonical"],
            family_id=row["family_id"],
            confidence=min(
                float(row["confidence_score"] or 0) + 0.05, 1.0
            ),
            match_method=MatchMethod.EXACT,
            requires_review=False,
            evidence=row["evidence"],
        )

    # ----------------------------------------------------------
    # NIVEAU 2 · Normalized sur canonical_slug
    # ----------------------------------------------------------
    row = conn.execute(
        """
        SELECT
            item_id,
            label_fr        AS canonical_form,
            default_unit    AS unit_canonical,
            family_id,
            confidence_score
        FROM couche_b.procurement_dict_items
        WHERE canonical_slug = %s
          AND active = TRUE
        LIMIT 1
        """,
        (normalized,),
    ).fetchone()

    if row:
        conf = float(row["confidence_score"] or 0)
        return MatchResult(
            item_id=row["item_id"],
            canonical_form=row["canonical_form"],
            unit_canonical=row["unit_canonical"],
            family_id=row["family_id"],
            confidence=conf,
            match_method=MatchMethod.NORMALIZED,
            requires_review=conf < 0.75,
            evidence=normalized,
        )

    # ----------------------------------------------------------
    # NIVEAU 3 · Trigram sur normalized_alias
    # Index gin_trgm_ops créé par M6 sur couche_b
    # ----------------------------------------------------------
    if _trgm_available(conn):
        row = conn.execute(
            """
            SELECT
                i.item_id,
                i.label_fr                          AS canonical_form,
                i.default_unit                      AS unit_canonical,
                i.family_id,
                i.confidence_score,
                a.normalized_alias                  AS evidence,
                similarity(a.normalized_alias, %s)  AS sim_score
            FROM couche_b.procurement_dict_aliases a
            JOIN couche_b.procurement_dict_items i
                ON i.item_id = a.item_id
            WHERE similarity(a.normalized_alias, %s) >= %s
              AND i.active = TRUE
            ORDER BY sim_score DESC
            LIMIT 1
            """,
            (normalized, normalized, TRIGRAM_THRESHOLD),
        ).fetchone()

        if row:
            sim  = float(row["sim_score"])
            conf = round(
                sim * float(row["confidence_score"] or 0), 4
            )
            return MatchResult(
                item_id=row["item_id"],
                canonical_form=row["canonical_form"],
                unit_canonical=row["unit_canonical"],
                family_id=row["family_id"],
                confidence=conf,
                match_method=MatchMethod.TRIGRAM,
                requires_review=True,
                evidence=(
                    f"trigram({row['evidence']},"
                    f"score={sim:.3f})"
                ),
            )

    # ----------------------------------------------------------
    # NIVEAU 4 · Non résolu · jamais silencieux
    # ----------------------------------------------------------
    logger.warning(
        "UNRESOLVED · raw='%s' · normalized='%s'",
        raw_label, normalized,
    )
    return MatchResult(
        item_id=None, canonical_form=None,
        unit_canonical=None, family_id=None,
        confidence=0.0,
        match_method=MatchMethod.UNRESOLVED,
        requires_review=True,
        evidence=normalized,
    )
