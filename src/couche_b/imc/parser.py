"""
Parser IMC — PDF INSTAT Mali · matériaux construction Bamako.

RÈGLE-30 : format confirmé par probe · pdfplumber pour extraction tabulaire.
Local-first · zéro LlamaCloud (PDF texte natif + tables structurées).
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _parse_filename_period(filename: str) -> tuple[int, int] | None:
    """Extrait (year, month) depuis AOUT18, JAN26, DEC25, AV25..."""
    stem = Path(filename).stem.upper()
    # Année 2 chiffres en fin
    year_m = re.search(r"(18|19|20|21|22|23|24|25|26)$", stem)
    if not year_m:
        return None
    yy = int(year_m.group(1))
    year = 2000 + yy if yy < 50 else 1900 + yy

    # Mois depuis préfixe
    for prefix, month in [
        ("JAN", 1),
        ("FEV", 2),
        ("MARS", 3),
        ("AVRIL", 4),
        ("AV", 4),  # AV25=avril
        ("MAI", 5),
        ("JUIN", 6),
        ("JUILLET", 7),
        ("JUI", 7),
        ("JULLET", 7),
        ("AOUT", 8),
        ("SEPT", 9),
        ("OCT", 10),
        ("NOV", 11),
        ("DEC", 12),
    ]:
        if stem.startswith(prefix) or prefix in stem[:6]:
            # AV peut matcher AVRIL - vérifier AVRIL avant AV
            if prefix == "AV" and "AVRIL" in stem:
                continue
            return (year, month)
    return None


def _clean_index(val: Any) -> Decimal | None:
    """Convertit 101,1 ou 101.1 → Decimal."""
    if val is None:
        return None
    s = str(val).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_imc_pdf(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse un PDF IMC INSTAT via pdfplumber.

    Retourne une liste de dicts · une entrée par ligne catégorie
    de matériau détectée dans le tableau.

    NOTE : les lignes articles détaillés sont ignorées.
    Le niveau d'agrégation retenu en M5-PATCH est la catégorie.
    La normalisation category_raw → category_normalized est différée.

    Chaque dict contient :
        category_raw  : str         · libellé brut extrait du PDF
        period_year   : int
        period_month  : int
        index_value   : float | None
        variation_mom : float | None
        variation_yoy : float | None
    """
    import pdfplumber

    period = _parse_filename_period(filepath.name)
    if not period:
        logger.warning("Période non détectée depuis fichier : %s", filepath.name)
        return []

    year, month = period
    entries: list[dict[str, Any]] = []
    current_category = ""

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 3:
                    continue

                for row in table[2:]:  # Skip header rows
                    if not row or len(row) < 5:
                        continue

                    code_raw = (row[0] or "").strip()
                    designation = (row[1] or "").strip()
                    # row[2] = UNITE, row[3] = PRIX, row[4] = INDICE (mois courant)
                    index_val = _clean_index(row[4])
                    # row[7] = variation MoM (août18/juillet18), row[8] = YoY
                    var_mom = _clean_index(row[7]) if len(row) > 7 else None
                    var_yoy = _clean_index(row[8]) if len(row) > 8 else None

                    # Ligne catégorie : code sans décimal (1, 3, 4) + designation = catégorie
                    # Une seule entrée par catégorie par période (UNIQUE source_id, category, period)
                    if code_raw and designation and "." not in code_raw:
                        try:
                            int(code_raw)
                            current_category = designation
                            # Output category-level row (index agrégé de la catégorie)
                            if index_val is not None:
                                entries.append(
                                    {
                                        "category_raw": current_category,
                                        "category_normalized": None,
                                        "period_year": year,
                                        "period_month": month,
                                        "index_value": index_val,
                                        "variation_mom": var_mom,
                                        "variation_yoy": var_yoy,
                                        "review_required": False,
                                    }
                                )
                            continue
                        except ValueError:
                            pass

                    # Ligne article : code avec décimal (1.2, 3.1) — ignorée pour imc_entries
                    # (schéma = 1 ligne par catégorie par période)

    logger.info("IMC parser · %s · %d entrées", filepath.name, len(entries))
    return entries
