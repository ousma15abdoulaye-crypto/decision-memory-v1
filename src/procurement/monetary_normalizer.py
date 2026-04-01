"""
M12 → M13 Prérequis — Normalisation monétaire.

Fonctions :
  normalize_monetary_value(text) → list[MonetaryValue]
    Parse les montants FCFA/XOF/USD/EUR depuis un texte en langage naturel.
    Gère les formats : "25 000 000 FCFA", "25M FCFA", "500.000.000 XOF",
    "50,000 USD", "50k USD".

  classify_dgmp_tier(amount_fcfa, family) → str
    Classe un montant FCFA en tier DGMP selon l'Art. 45-46 du Code des Marchés.
    Tiers : "gre_a_gre" | "aon" | "aoi"

  SCI_DGMP_OVERLAP_ZONE_USD — constante documentant l'écart SCI/DGMP.

Toutes les valeurs normalisées sont en FCFA (devise canonique DMS/Mali).
Taux de conversion : 1 USD = 600 FCFA (palier conservateur UEMOA 2025).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Taux de conversion (conservateur UEMOA 2025) ──────────────────────────
_USD_TO_FCFA: float = 600.0
_EUR_TO_FCFA: float = 655.957  # parité fixe XOF/EUR

# ── Seuils DGMP Art. 45-46 (FCFA) ─────────────────────────────────────────
# Source : Code des Marchés Publics 2015
_DGMP_AON_GOODS_SERVICES_FCFA: float = 25_000_000.0
_DGMP_AON_WORKS_FCFA: float = 100_000_000.0
_DGMP_AOI_FCFA: float = 500_000_000.0

# ── Écart de recouvrement SCI ↔ DGMP ──────────────────────────────────────
# SCI ITB upper bound : 50 000 USD = 30 000 000 FCFA (@ 600 FCFA/USD)
# DGMP AON lower bound : 25 000 000 FCFA ≈ 41 667 USD
# Zone de recouvrement : 25M–30M FCFA (41 667–50 000 USD)
# Tout document dans cette zone est potentiellement soumis aux deux cadres.
SCI_DGMP_OVERLAP_ZONE_USD: dict[str, float] = {
    "min_usd": _DGMP_AON_GOODS_SERVICES_FCFA / _USD_TO_FCFA,  # ~41 667
    "max_usd": 50_000.0,  # SCI ITB upper bound
    "min_fcfa": _DGMP_AON_GOODS_SERVICES_FCFA,
    "max_fcfa": 50_000.0 * _USD_TO_FCFA,  # 30 000 000
}

# ── Patterns de parsing ───────────────────────────────────────────────────

# Suffixes multiplicateurs : 25M, 500K, 1 000 000, 1.000.000, 1,000,000
_MULT: dict[str, float] = {
    "m": 1_000_000.0,
    "mm": 1_000_000.0,
    "millions": 1_000_000.0,
    "million": 1_000_000.0,
    "k": 1_000.0,
    "mille": 1_000.0,
    "milliards": 1_000_000_000.0,
    "milliard": 1_000_000_000.0,
    "b": 1_000_000_000.0,
}

# Devises reconnues → code ISO
_CURRENCY_ALIASES: dict[str, str] = {
    "fcfa": "XOF",
    "xof": "XOF",
    "cfa": "XOF",
    "f cfa": "XOF",
    "franc cfa": "XOF",
    "usd": "USD",
    "$": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "us$": "USD",
    "eur": "EUR",
    "€": "EUR",
    "euro": "EUR",
    "euros": "EUR",
}

_PATTERN = re.compile(
    r"(?P<amount>"
    r"\d{1,3}(?:[., ]\d{3})*(?:[.,]\d+)?"  # 1,000,000 / 1.000.000 / 1 000 000
    r"|\d+"
    r")"
    r"\s*"
    r"(?P<mult>millions?|milliards?|mille|mm|m|k|b)?"
    r"\s*"
    r"(?P<currency>FCFA|XOF|CFA|F CFA|Franc CFA|USD|\$|US\$|EUR|€|euros?|dollars?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MonetaryValue:
    """Valeur monétaire normalisée extraite d'un texte."""

    raw: str
    amount_native: float
    currency_iso: str
    amount_fcfa: float


def normalize_monetary_value(text: str) -> list[MonetaryValue]:
    """Parse toutes les valeurs monétaires d'un texte en langage naturel.

    Retourne une liste de MonetaryValue triée par amount_fcfa décroissant.
    Retourne [] si aucune valeur n'est trouvée.

    Exemples acceptés :
      "25 000 000 FCFA"  → 25_000_000 XOF
      "25M FCFA"         → 25_000_000 XOF
      "500.000.000 XOF"  → 500_000_000 XOF
      "50,000 USD"       → 50_000 USD → 30_000_000 FCFA
      "500K USD"         → 500_000 USD → 300_000_000 FCFA
    """
    results: list[MonetaryValue] = []
    for m in _PATTERN.finditer(text):
        raw_amount = m.group("amount")
        raw_mult = (m.group("mult") or "").lower().strip()
        raw_currency = m.group("currency").lower().strip()

        amount_str = re.sub(r"[., ](\d{3})", r"\1", raw_amount)
        amount_str = amount_str.replace(",", ".").replace(" ", "")
        try:
            amount = float(amount_str)
        except ValueError:
            continue

        mult = _MULT.get(raw_mult, 1.0)
        amount_native = amount * mult

        currency_iso = _CURRENCY_ALIASES.get(raw_currency, raw_currency.upper())

        if currency_iso == "XOF":
            amount_fcfa = amount_native
        elif currency_iso == "USD":
            amount_fcfa = amount_native * _USD_TO_FCFA
        elif currency_iso == "EUR":
            amount_fcfa = amount_native * _EUR_TO_FCFA
        else:
            amount_fcfa = amount_native

        results.append(
            MonetaryValue(
                raw=m.group(0).strip(),
                amount_native=amount_native,
                currency_iso=currency_iso,
                amount_fcfa=amount_fcfa,
            )
        )

    results.sort(key=lambda v: v.amount_fcfa, reverse=True)
    return results


def classify_dgmp_tier(
    amount_fcfa: float,
    family: str = "goods_services",
) -> str:
    """Classe un montant FCFA en tier DGMP (Art. 45-46).

    Args:
        amount_fcfa: Montant en FCFA.
        family: "works" pour travaux, "goods_services" (défaut) pour biens/services.

    Returns:
        "gre_a_gre" | "aon" | "aoi"
    """
    aon_floor = (
        _DGMP_AON_WORKS_FCFA
        if family.lower() in ("works", "travaux")
        else _DGMP_AON_GOODS_SERVICES_FCFA
    )

    if amount_fcfa < aon_floor:
        return "gre_a_gre"
    if amount_fcfa < _DGMP_AOI_FCFA:
        return "aon"
    return "aoi"
