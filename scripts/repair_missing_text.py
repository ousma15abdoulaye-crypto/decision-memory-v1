#!/usr/bin/env python3
"""Ré-OCR des ``bundle_documents`` sans ``raw_text`` pour un workspace.

Usage::
    python scripts/repair_missing_text.py --workspace-id <UUID> [--dry-run] [--re-extract]

Exige ``DATABASE_URL``, RLS admin (script pose ``app.is_admin``), et chemins
``storage_path`` encore lisibles sur le disque (sinon diagnostic seulement).

La ré-extraction des offres (``--re-extract``) appelle ``extract_offers_from_bundles``
du service pipeline V5 (Mistral / backend selon config).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repair_missing_text")


async def _ocr_file(path: Path) -> dict:
    from src.assembler.graph import _extract_excel, _extract_word
    from src.assembler.ocr_azure import ocr_with_azure
    from src.assembler.ocr_mistral import ocr_native_pdf, ocr_with_mistral
    from src.assembler.pdf_detector import FileType, detect_file_type

    ft = detect_file_type(path)
    if ft == FileType.NATIVE_PDF:
        r = await ocr_native_pdf(path)
        if len((r.get("raw_text") or "").strip()) >= 40:
            return r
        r2 = await ocr_with_mistral(path)
        if len((r2.get("raw_text") or "").strip()) >= 20:
            return r2
        return await ocr_with_azure(path)
    if ft in {FileType.SCAN, FileType.IMAGE}:
        r = await ocr_with_mistral(path)
        if len((r.get("raw_text") or "").strip()) >= 10:
            return r
        return await ocr_with_azure(path)
    if ft == FileType.WORD:
        return _extract_word(path)
    if ft == FileType.EXCEL:
        return _extract_excel(path)
    return {
        "raw_text": "",
        "confidence": 0.0,
        "ocr_engine": "none",
        "error": "unsupported_type",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", required=True, help="UUID process_workspaces")
    parser.add_argument("--dry-run", action="store_true", help="Ne pas écrire en base")
    parser.add_argument(
        "--re-extract",
        action="store_true",
        help="Après mise à jour du texte, relancer extract_offers_from_bundles",
    )
    args = parser.parse_args()

    from src.db import db_execute, db_execute_one, db_fetchall, get_connection
    from src.db.tenant_context import reset_rls_request_context, set_rls_is_admin
    from src.services.pipeline_v5_service import extract_offers_from_bundles

    wid = args.workspace_id.strip()
    set_rls_is_admin(True)
    try:
        with get_connection() as conn:
            rows = db_fetchall(
                conn,
                """
                SELECT id::text AS id, storage_path, filename, file_type
                FROM bundle_documents
                WHERE workspace_id = CAST(:wid AS uuid)
                  AND (raw_text IS NULL OR trim(raw_text) = '')
                ORDER BY uploaded_at
                """,
                {"wid": wid},
            )
            if not rows:
                logger.info("Aucun document sans texte pour workspace=%s", wid)
                return

            logger.info("%d document(s) à traiter", len(rows))
            repaired = 0
            for row in rows:
                sp = (row.get("storage_path") or "").strip()
                p = Path(sp)
                if not p.is_file():
                    logger.error(
                        "Fichier introuvable — id=%s path=%s filename=%s "
                        "(PDF scanné déplacé ? import depuis autre machine ?)",
                        row["id"],
                        sp,
                        row.get("filename"),
                    )
                    continue
                ocr = asyncio.run(_ocr_file(p))
                text = (ocr.get("raw_text") or "").strip()
                if not text:
                    logger.error(
                        "OCR vide — id=%s file=%s engine=%s err=%s",
                        row["id"],
                        p.name,
                        ocr.get("ocr_engine"),
                        ocr.get("error"),
                    )
                    continue
                text = text.replace("\x00", "")
                logger.info(
                    "OK id=%s chars=%d engine=%s",
                    row["id"],
                    len(text),
                    ocr.get("ocr_engine"),
                )
                repaired += 1
                if args.dry_run:
                    continue
                db_execute(
                    conn,
                    """
                    UPDATE bundle_documents
                    SET raw_text = :rt,
                        ocr_engine = :eng,
                        ocr_confidence = :conf
                    WHERE id = CAST(:id AS uuid)
                    """,
                    {
                        "rt": text,
                        "eng": ocr.get("ocr_engine"),
                        "conf": ocr.get("confidence"),
                        "id": row["id"],
                    },
                )

        if args.re_extract and not args.dry_run and repaired > 0:
            ws = None
            with get_connection() as conn2:
                ws = db_execute_one(
                    conn2,
                    """
                    SELECT legacy_case_id::text AS legacy_case_id
                    FROM process_workspaces
                    WHERE id = CAST(:wid AS uuid)
                    """,
                    {"wid": wid},
                )
            case_id = ws.get("legacy_case_id") if ws else None
            if not case_id:
                logger.error("legacy_case_id manquant — ré-extraction ignorée")
                return
            n, _failed = extract_offers_from_bundles(wid, case_id)
            logger.info("Ré-extraction offres terminée — succès=%s", n)
    finally:
        reset_rls_request_context()


if __name__ == "__main__":
    main()
