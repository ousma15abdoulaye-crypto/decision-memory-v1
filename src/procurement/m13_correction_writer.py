"""
M13 Correction Log Writer.

Écrit les corrections humaines dans ``m13_correction_log`` (migration 057).
Append-only : pas d'UPDATE ni DELETE au niveau applicatif ; triggers DB en renfort.

Schéma réel (057) : ``case_id`` (FK cases), ``field_path``, ``value_predicted``,
``value_corrected`` (TEXT), ``layer_origin``, ``confidence_was`` (DOUBLE PRECISION),
``correction_source``, ``corpus_size_at_correction`` (INTEGER), ``created_at``.

Connexion : ``src.db.core._ConnectionWrapper`` (``execute`` / ``fetchone`` / ``fetchall``),
pas SQLAlchemy ``AsyncSession``.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

_MAX_RECENT_LIMIT = 1000


class M13CorrectionEntry(BaseModel):
    """Une correction humaine M13 — validée avant insertion (E-49 : extra forbid)."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1, description="ID du case corrigé (FK cases)")
    field_path: str = Field(
        ...,
        min_length=1,
        description="Chemin du champ corrigé (ex. regime.procedure_type)",
    )
    value_predicted: str | None = Field(
        default=None,
        description="Valeur prédite par M13 (TEXT)",
    )
    value_corrected: str | None = Field(
        default=None,
        description="Valeur corrigée par l'humain (TEXT)",
    )
    layer_origin: str | None = Field(
        default=None,
        description="Couche d'origine (ex. regime_resolver, gate_assembler, principles)",
    )
    confidence_was: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confiance M13 avant correction",
    )
    correction_source: str | None = Field(
        default=None,
        description="Source de correction (ex. human_annotator, senior_reviewer)",
    )
    corpus_size_at_correction: int | None = Field(
        default=None,
        ge=0,
        description="Taille corpus au moment de la correction",
    )

    def resolved_metadata_json(self) -> str | None:
        """JSON des métadonnées optionnelles pour traçabilité étendue."""
        meta: dict[str, Any] = {}
        if self.layer_origin is not None:
            meta["layer_origin"] = self.layer_origin
        if self.confidence_was is not None:
            meta["confidence_was"] = self.confidence_was
        if self.corpus_size_at_correction is not None:
            meta["corpus_size_at_correction"] = self.corpus_size_at_correction
        if not meta:
            return None
        return json.dumps(meta, ensure_ascii=False)


@runtime_checkable
class _CorrectionLogConnection(Protocol):
    """Protocole minimal — ``_ConnectionWrapper`` ou mock tests."""

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None: ...

    def fetchone(self) -> dict[str, Any] | None: ...

    def fetchall(self) -> list[dict[str, Any]]: ...


class M13CorrectionWriter:
    """
    Writer append-only pour ``m13_correction_log``.

    Pas de UPDATE / DELETE / recalibration / notification.
    """

    _INSERT_SQL = """
        INSERT INTO m13_correction_log (
            case_id,
            field_path,
            value_predicted,
            value_corrected,
            layer_origin,
            confidence_was,
            correction_source,
            corpus_size_at_correction
        ) VALUES (
            :case_id,
            :field_path,
            :value_predicted,
            :value_corrected,
            :layer_origin,
            :confidence_was,
            :correction_source,
            :corpus_size_at_correction
        )
        RETURNING id
    """

    _COUNT_SQL = "SELECT COUNT(*) AS c FROM m13_correction_log"

    _COUNT_BY_FIELD_SQL = """
        SELECT COUNT(*) AS c FROM m13_correction_log
        WHERE field_path = :field_path
    """

    _COUNT_BY_CASE_SQL = """
        SELECT COUNT(*) AS c FROM m13_correction_log
        WHERE case_id = :case_id
    """

    _RECENT_SQL = """
        SELECT * FROM m13_correction_log
        ORDER BY created_at DESC
        LIMIT :limit
    """

    _RATE_LAST_30D_SQL = """
        SELECT
            COUNT(*) AS corrections,
            COUNT(DISTINCT case_id) AS cases_corrected
        FROM m13_correction_log
        WHERE created_at >= NOW() - INTERVAL '30 days'
    """

    def write(self, conn: _CorrectionLogConnection, entry: M13CorrectionEntry) -> int:
        """Insère une correction. Retourne l'id (BIGSERIAL)."""
        params: dict[str, Any] = {
            "case_id": entry.case_id,
            "field_path": entry.field_path,
            "value_predicted": entry.value_predicted,
            "value_corrected": entry.value_corrected,
            "layer_origin": entry.layer_origin,
            "confidence_was": entry.confidence_was,
            "correction_source": entry.correction_source,
            "corpus_size_at_correction": entry.corpus_size_at_correction,
        }
        conn.execute(self._INSERT_SQL, params)
        row = conn.fetchone()
        if row is None or "id" not in row:
            raise RuntimeError("m13_correction_log INSERT did not RETURNING id")
        return int(row["id"])

    def write_batch(
        self,
        conn: _CorrectionLogConnection,
        entries: list[M13CorrectionEntry],
    ) -> list[int]:
        """Insère N corrections dans la même transaction (même connexion)."""
        return [self.write(conn, e) for e in entries]

    def count_total(self, conn: _CorrectionLogConnection) -> int:
        conn.execute(self._COUNT_SQL, {})
        row = conn.fetchone()
        if row is None:
            return 0
        return int(row["c"])

    def count_by_field(self, conn: _CorrectionLogConnection, field_path: str) -> int:
        """Nombre de corrections pour un ``field_path`` donné."""
        conn.execute(self._COUNT_BY_FIELD_SQL, {"field_path": field_path})
        row = conn.fetchone()
        if row is None:
            return 0
        return int(row["c"])

    def count_by_case(self, conn: _CorrectionLogConnection, case_id: str) -> int:
        conn.execute(self._COUNT_BY_CASE_SQL, {"case_id": case_id})
        row = conn.fetchone()
        if row is None:
            return 0
        return int(row["c"])

    def get_recent(
        self, conn: _CorrectionLogConnection, limit: int = 20
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        effective = min(limit, _MAX_RECENT_LIMIT)
        conn.execute(self._RECENT_SQL, {"limit": effective})
        return conn.fetchall()

    def rate_last_30d(self, conn: _CorrectionLogConnection) -> float:
        """
        Ratio corrections / cases distincts sur 30 jours.
        0.0 si aucun case distinct corrigé.
        """
        conn.execute(self._RATE_LAST_30D_SQL, {})
        row = conn.fetchone()
        if row is None:
            return 0.0
        corrections = int(row["corrections"] or 0)
        cases = int(row["cases_corrected"] or 0)
        if cases == 0:
            return 0.0
        return corrections / cases
