"""
Aperçu structuré minimal pour les tâches Label Studio (ADR P2).

Utilise pdfplumber.extract_tables sur les premières pages — métadonnées seulement
(nombre de lignes/colonnes), sans dupliquer tout le tableau dans la charge utile.
"""

from __future__ import annotations

from typing import Any

_MAX_TABLES_TOTAL = 40


def structured_preview_from_pdf(
    path: str,
    *,
    max_pages: int = 5,
) -> dict[str, Any]:
    """
    Retourne un dict sérialisable JSON pour ``data.structured_preview`` (LS).

    max_pages=0 → retour minimal sans lecture fichier.
    """
    empty: dict[str, Any] = {
        "version": 1,
        "engine": "pdfplumber_extract_tables",
        "source_path_hint": path,
        "page_count_sampled": 0,
        "tables": [],
        "errors": [],
    }
    if max_pages <= 0:
        empty["errors"].append("structured_preview_disabled")
        return empty

    try:
        import pdfplumber  # type: ignore
    except ImportError:
        empty["errors"].append("pdfplumber_missing")
        return empty

    tables_out: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        with pdfplumber.open(path) as pdf:
            n = min(len(pdf.pages), max_pages)
            empty["page_count_sampled"] = n
            for i in range(n):
                page = pdf.pages[i]
                raw_tables = page.extract_tables() or []
                for ti, table in enumerate(raw_tables):
                    if len(tables_out) >= _MAX_TABLES_TOTAL:
                        break
                    rows = len(table) if table else 0
                    cols = len(table[0]) if table and table[0] else 0
                    tables_out.append(
                        {
                            "page_index": i + 1,
                            "table_index": ti,
                            "rows": rows,
                            "cols": cols,
                        }
                    )
                if len(tables_out) >= _MAX_TABLES_TOTAL:
                    break
    except OSError as e:
        errors.append(f"os:{e!s}"[:200])
    except Exception as e:
        errors.append(f"{type(e).__name__}:{e!s}"[:200])

    empty["tables"] = tables_out
    empty["errors"] = errors
    return empty
