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

# Mapping nom fichier → (year, month)
_MONTH_NAMES: dict[str, int] = {
    "jan": 1,
    "janvier": 1,
    "fev": 2,
    "fevrier": 2,
    "av": 2,  # AV25 = avril? non, FEV=février
    "mars": 3,
    "mars": 3,
    "avril": 4,
    "avr": 4,
    "av": 4,
    "mai": 5,
    "juin": 6,
    "juin": 6,
    "juillet": 7,
    "jui": 7,
    "juil": 7,
    "jull": 7,  # JULLET21 typo
    "aout": 8,
    "aout": 8,
    "aout": 8,
    "sept": 9,
    "septembre": 9,
    "oct": 10,
    "octobre": 10,
    "nov": 11,
    "novembre": 11,
    "dec": 12,
    "decembre": 12,
}


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
    Parse un PDF IMC INSTAT → liste d'entrées pour imc_entries.

    Retourne une entrée par ligne article (pas les lignes catégorie).
    category_raw = catégorie section (BOIS, AGREGATS, etc.)
    index_value = indice du mois courant (col août-18)
    variation_mom = août18/juillet18
    variation_yoy = août18/août17
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
                    unite = (row[2] or "").strip()
                    # row[3] = PRIX, row[4] = INDICE (mois courant)
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
