#!/usr/bin/env python3
# scripts/test_extraction_e2e.py
"""
Test E2E extraction réelle — Mandat 4 — DMS v4.1

UN vrai document anonymisé traverse le pipeline.
Ce script prouve que le pont fonctionne sur données réelles.

Usage :
  ANNOTATION_BACKEND_URL=https://annotation-backend.railway.app \
  MISTRAL_API_KEY=sk-... \
  python scripts/test_extraction_e2e.py <chemin_doc>

Condition DONE Mandat 4 :
  extraction_ok=True ET family_main != ABSENT
"""

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("e2e")


async def run(doc_path: str) -> int:
    from src.couche_a.extraction import (
        extract_offer_content_async,
        extract_text_any,
    )

    path = Path(doc_path)
    if not path.exists():
        logger.error("Fichier introuvable : %s", doc_path)
        return 1

    logger.info("Document : %s", path.name)
    text = extract_text_any(str(path))
    logger.info("Texte extrait : %d chars", len(text))

    if not text.strip():
        logger.error("Texte vide — vérifier le fichier")
        return 1

    result = await extract_offer_content_async(
        document_id=f"e2e-{path.stem}",
        text=text,
        document_role="financial_offer",
    )

    print("\n" + "=" * 60)
    print("RÉSULTAT EXTRACTION E2E — DMS v4.1")
    print("=" * 60)
    print(f"document_id     : {result.document_id}")
    print(f"extraction_ok   : {result.extraction_ok}")
    print(f"review_required : {result.review_required}")
    print(f"family_main     : {result.family_main}")
    print(f"family_sub      : {result.family_sub}")
    print(f"taxonomy_core   : {result.taxonomy_core}")
    print(f"tier_used       : {result.tier_used.value}")
    print(f"latency_ms      : {result.latency_ms:.0f}ms")
    print(f"fields          : {len(result.fields)}")
    print(f"line_items      : {len(result.line_items)}")
    print(f"gates           : {len(result.gates)}")
    print(f"ambiguites      : {result.ambiguites}")
    print(f"error_reason    : {result.error_reason}")

    if result.fields:
        print("\n── FIELDS (5 premiers) ──")
        for f in result.fields[:5]:
            print(
                f"  {f.field_name:<30} "
                f"conf={f.confidence} "
                f"val={str(f.value)[:40]}"
            )

    if result.line_items:
        print("\n── LINE ITEMS ──")
        for li in result.line_items:
            print(
                f"  #{li.item_line_no} "
                f"{li.item_description_raw[:35]:<35} "
                f"qty={li.quantity} "
                f"unit={li.unit_raw} "
                f"total={li.line_total} "
                f"[{li.line_total_check}]"
            )

    print("\n── VERDICT ──")
    if result.extraction_ok and result.family_main != "ABSENT":
        print("✅ CONDITION DONE MANDAT 4 SATISFAITE")
        print(
            f"   {result.family_main}/"
            f"{result.family_sub}/"
            f"{result.taxonomy_core}"
        )
        return 0
    elif result.review_required:
        print("⚠️  review_required — validation humaine requise")
        print(f"   Raison : {result.error_reason}")
        return 1
    else:
        print("❌ EXTRACTION ÉCHOUÉE")
        print(f"   Raison : {result.error_reason}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <doc.pdf|doc.txt>")
        sys.exit(1)
    sys.exit(asyncio.run(run(sys.argv[1])))
