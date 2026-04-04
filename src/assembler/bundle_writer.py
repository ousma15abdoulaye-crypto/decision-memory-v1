"""Écriture des supplier_bundles et bundle_documents en base — Pass -1.

Idempotent : UNIQUE(workspace_id, sha256) sur bundle_documents
évite les doublons lors de rejeu ARQ.

Référence : Plan V4.2.0 Phase 4 — src/assembler/bundle_writer.py
Migration 070 (supplier_bundles, bundle_documents).
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path

from src.db import db_execute, db_execute_one, get_connection

logger = logging.getLogger(__name__)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_bundle(
    workspace_id: str,
    tenant_id: str,
    vendor_name_raw: str,
    bundle_index: int,
    documents: list[dict],
    completeness_score: float,
    missing_documents: list[str],
    hitl_required: bool,
    vendor_id: str | None = None,
) -> str:
    """Écrit un bundle fournisseur et ses documents en base.

    Idempotent — si le bundle avec ce bundle_index existe déjà dans ce workspace,
    retourne son id sans créer de doublon.

    Args:
        workspace_id: UUID du workspace.
        tenant_id: UUID du tenant.
        vendor_name_raw: Nom brut du fournisseur.
        bundle_index: Index ordinal du bundle dans le workspace (UNIQUE).
        documents: Liste de dicts avec keys: path, doc_type, doc_role, m12_doc_kind, ocr_result.
        completeness_score: Score de complétude (0.0 → 1.0).
        missing_documents: Liste des types de docs manquants.
        hitl_required: Si True, interruption HITL requise avant finalisation.
        vendor_id: UUID du fournisseur résolu (optionnel).

    Returns:
        UUID du supplier_bundle créé ou existant.
    """
    with get_connection() as conn:
        existing = db_execute_one(
            conn,
            """
            SELECT id FROM supplier_bundles
            WHERE workspace_id = :ws AND bundle_index = :idx
            """,
            {"ws": workspace_id, "idx": bundle_index},
        )
        if existing:
            bundle_id = str(existing["id"])
            logger.info(
                "[BUNDLE-WRITER] Bundle index=%d workspace=%s existe déjà : %s",
                bundle_index,
                workspace_id,
                bundle_id,
            )
            return bundle_id

        bundle_id = str(uuid.uuid4())
        db_execute(
            conn,
            """
            INSERT INTO supplier_bundles (
                id, workspace_id, tenant_id, vendor_name_raw, vendor_id,
                bundle_status, completeness_score, missing_documents,
                hitl_required, bundle_index, assembled_by, assembled_at
            ) VALUES (
                :id, :ws, :tid, :vendor, :vid,
                :status, :score, :missing,
                :hitl, :idx, 'pass_minus_1', NOW()
            )
            """,
            {
                "id": bundle_id,
                "ws": workspace_id,
                "tid": tenant_id,
                "vendor": vendor_name_raw,
                "vid": vendor_id,
                "status": "incomplete" if hitl_required else "assembling",
                "score": completeness_score,
                "missing": missing_documents or [],
                "hitl": hitl_required,
                "idx": bundle_index,
            },
        )

        for doc in documents:
            file_path = Path(doc.get("storage_path", doc.get("path", "")))
            sha256 = doc.get("sha256") or (
                _sha256_file(file_path) if file_path.exists() else str(uuid.uuid4())
            )

            ocr = doc.get("ocr_result", {})
            db_execute(
                conn,
                """
                INSERT INTO bundle_documents (
                    id, bundle_id, workspace_id, tenant_id,
                    doc_type, doc_role, filename, sha256, file_type,
                    storage_path, ocr_engine, ocr_confidence, raw_text,
                    structured_json, m12_doc_kind, m12_confidence,
                    uploaded_at
                ) VALUES (
                    :id, :bid, :ws, :tid,
                    :dtype, :drole, :fname, :sha, :ftype,
                    :spath, :oengine, :oconf, :rawtext,
                    :sjson, :m12kind, :m12conf,
                    NOW()
                )
                ON CONFLICT (workspace_id, sha256) DO NOTHING
                """,
                {
                    "id": str(uuid.uuid4()),
                    "bid": bundle_id,
                    "ws": workspace_id,
                    "tid": tenant_id,
                    "dtype": doc.get("doc_type", "other"),
                    "drole": doc.get("doc_role", "unknown"),
                    "fname": file_path.name if file_path else doc.get("filename", ""),
                    "sha": sha256,
                    "ftype": doc.get("file_type", "unknown"),
                    "spath": str(file_path) if file_path else "",
                    "oengine": ocr.get("ocr_engine"),
                    "oconf": ocr.get("confidence"),
                    "rawtext": ocr.get("raw_text"),
                    "sjson": None,
                    "m12kind": doc.get("m12_doc_kind"),
                    "m12conf": doc.get("m12_confidence"),
                },
            )

    logger.info(
        "[BUNDLE-WRITER] Bundle %s créé (index=%d, docs=%d, hitl=%s)",
        bundle_id,
        bundle_index,
        len(documents),
        hitl_required,
    )
    return bundle_id
