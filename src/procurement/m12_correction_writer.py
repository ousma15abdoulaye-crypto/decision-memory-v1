"""
M12 Correction Log Writer.

Écrit les corrections humaines dans ``m12_correction_log`` (migration 054).
Append-only : pas d'UPDATE ni DELETE au niveau applicatif ; triggers DB en renfort.

Schéma réel : ``document_id``, ``run_id``, ``correction_type``, ``field_corrected``,
``original_value`` / ``corrected_value`` (JSONB), ``corrected_by``, ``correction_note``,
``created_at``.

Connexion : ``src.db.core._ConnectionWrapper`` (``execute`` / ``fetchone`` / ``fetchall``),
pas SQLAlchemy ``AsyncSession``.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# CHECK (054) — valeurs exactes
M12_CORRECTION_TYPES = frozenset(
    (
        "framework",
        "family",
        "document_kind",
        "subtype",
        "validity",
        "conformity",
        "process_link",
        "other",
    )
)


class M12CorrectionEntry(BaseModel):
    """Une correction humaine — validée avant insertion (E-49 : extra forbid)."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., min_length=1, description="ID du document corrigé")
    run_id: UUID = Field(..., description="Run pipeline M12 (obligatoire en 054)")
    correction_type: str = Field(
        ...,
        description="Type aligné migration 054 (framework, family, document_kind, …)",
    )
    field_corrected: str = Field(
        ...,
        min_length=1,
        description="Champ corrigé (ex. procedure_recognition.document_kind)",
    )
    original_value: dict[str, Any] = Field(
        default_factory=dict,
        description="Valeur avant correction (JSONB)",
    )
    corrected_value: dict[str, Any] = Field(
        default_factory=dict,
        description="Valeur après correction (JSONB)",
    )
    corrected_by: str = Field(
        ...,
        min_length=1,
        description="Source (ex. human, human_annotator)",
    )
    correction_note: str | None = Field(
        default=None,
        description="Note libre ; sinon métadonnées optionnelles sérialisées en JSON",
    )
    pass_origin: str | None = Field(
        default=None,
        description="Sous-passe d'origine (1A, 1B, …) — fusionnée dans correction_note",
    )
    confidence_was: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confiance M12 avant correction",
    )
    corpus_size_at_correction: int | None = Field(
        default=None,
        ge=0,
        description="Taille corpus au moment de la correction",
    )

    @model_validator(mode="after")
    def _validate_correction_type(self) -> M12CorrectionEntry:
        if self.correction_type not in M12_CORRECTION_TYPES:
            raise ValueError(
                f"correction_type must be one of {sorted(M12_CORRECTION_TYPES)}"
            )
        return self

    def resolved_correction_note(self) -> str | None:
        """Note finale : explicite ou JSON des métadonnées optionnelles."""
        if self.correction_note is not None:
            return self.correction_note
        meta: dict[str, Any] = {}
        if self.pass_origin is not None:
            meta["pass_origin"] = self.pass_origin
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


class M12CorrectionWriter:
    """
    Writer append-only pour ``m12_correction_log``.

    Pas de UPDATE / DELETE / recalibration / notification.
    """

    _INSERT_SQL = """
        INSERT INTO m12_correction_log (
            document_id,
            run_id,
            correction_type,
            field_corrected,
            original_value,
            corrected_value,
            corrected_by,
            correction_note
        ) VALUES (
            :document_id,
            :run_id,
            :correction_type,
            :field_corrected,
            :original_value,
            :corrected_value,
            :corrected_by,
            :correction_note
        )
        RETURNING id
    """

    _COUNT_SQL = "SELECT COUNT(*) AS c FROM m12_correction_log"

    _COUNT_BY_FIELD_SQL = """
        SELECT COUNT(*) AS c FROM m12_correction_log
        WHERE field_corrected = :field_corrected
    """

    _COUNT_BY_DOCUMENT_SQL = """
        SELECT COUNT(*) AS c FROM m12_correction_log
        WHERE document_id = :document_id
    """

    _RECENT_SQL = """
        SELECT * FROM m12_correction_log
        ORDER BY created_at DESC
        LIMIT :limit
    """

    _RATE_LAST_30D_SQL = """
        SELECT
            COUNT(*) AS corrections,
            (SELECT COUNT(DISTINCT document_id)
             FROM m12_correction_log
             WHERE created_at >= NOW() - INTERVAL '30 days'
            ) AS documents_corrected
        FROM m12_correction_log
        WHERE created_at >= NOW() - INTERVAL '30 days'
    """

    def write(self, conn: _CorrectionLogConnection, entry: M12CorrectionEntry) -> int:
        """Insère une correction. Retourne l'id (BIGSERIAL)."""
        note = entry.resolved_correction_note()
        params: dict[str, Any] = {
            "document_id": entry.document_id,
            "run_id": str(entry.run_id),
            "correction_type": entry.correction_type,
            "field_corrected": entry.field_corrected,
            "original_value": entry.original_value,
            "corrected_value": entry.corrected_value,
            "corrected_by": entry.corrected_by,
            "correction_note": note,
        }
        conn.execute(self._INSERT_SQL, params)
        row = conn.fetchone()
        if row is None or "id" not in row:
            raise RuntimeError("m12_correction_log INSERT did not RETURNING id")
        return int(row["id"])

    def write_batch(
        self,
        conn: _CorrectionLogConnection,
        entries: list[M12CorrectionEntry],
    ) -> list[int]:
        """Insère N corrections dans la même transaction (même connexion)."""
        return [self.write(conn, e) for e in entries]

    def count_total(self, conn: _CorrectionLogConnection) -> int:
        conn.execute(self._COUNT_SQL, {})
        row = conn.fetchone()
        if row is None:
            return 0
        return int(row["c"])

    def count_by_field(
        self, conn: _CorrectionLogConnection, field_corrected: str
    ) -> int:
        """Nombre de corrections pour un ``field_corrected`` donné."""
        conn.execute(
            self._COUNT_BY_FIELD_SQL,
            {"field_corrected": field_corrected},
        )
        row = conn.fetchone()
        if row is None:
            return 0
        return int(row["c"])

    def count_by_document(
        self, conn: _CorrectionLogConnection, document_id: str
    ) -> int:
        conn.execute(
            self._COUNT_BY_DOCUMENT_SQL,
            {"document_id": document_id},
        )
        row = conn.fetchone()
        if row is None:
            return 0
        return int(row["c"])

    def get_recent(
        self, conn: _CorrectionLogConnection, limit: int = 20
    ) -> list[dict[str, Any]]:
        conn.execute(self._RECENT_SQL, {"limit": limit})
        return conn.fetchall()

    def rate_last_30d(self, conn: _CorrectionLogConnection) -> float:
        """
        Ratio corrections / documents distincts sur 30 jours.
        0.0 si aucun document distinct corrigé.
        """
        conn.execute(self._RATE_LAST_30D_SQL, {})
        row = conn.fetchone()
        if row is None:
            return 0.0
        corrections = int(row["corrections"] or 0)
        documents = int(row["documents_corrected"] or 0)
        if documents == 0:
            return 0.0
        return corrections / documents
