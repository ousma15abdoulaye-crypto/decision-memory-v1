"""Heuristiques lexicales — requêtes marché factuelles vs recommandation (INV-W06).

Le routeur par embeddings (Mistral) peut encore classer RECOMMENDATION ≥ 0.85 pour
des questions prix (« marché » public, « fournisseurs » dans les exemples marché).
Ce module fournit un passage sûr **avant** le blocage guardrail : uniquement si la
phrase ressemble à une demande de **donnée prix / tarif** et non à un choix d’offre.
"""

from __future__ import annotations

import re
import unicodedata

# Demande explicite de donnée de prix / coût (référence marché, pas « qui gagner »)
_PRICE_HINT = re.compile(
    r"(?:"
    r"\b("
    r"prix|tarif|tarifs|"
    r"co[uû]t|cout|coute|coûte|"
    r"combien|"
    r"xof|cfa|fcfa|euro|eur"
    r")\b"
    r"|"
    r"(?<!\w)€(?!\w)"
    r")",
    re.IGNORECASE,
)

# Tournures de prescription / classement / attribution (ne pas court-circuiter le guardrail)
_RECOMMENDATION_HINT = re.compile(
    r"\b("
    r"meilleur|meilleure|"
    r"gagnant|gagnante|"
    r"recommand|conseil.{0,12}fournisseur|"
    r"classez|classer|classement|"
    r"moins[- ]?disant|"
    r"qui.{0,20}choisir|"
    r"attribuer.{0,20}march|"
    r"remporter.{0,20}contrat|"
    r"quel fournisseur.{0,25}(choisir|retenir|privil)"
    r")\b",
    re.IGNORECASE,
)


def _fold(text: str) -> str:
    """Minuscules + suppression des diacritiques pour matcher prix/coût/côte."""
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def looks_like_factual_market_price_query(query: str) -> bool:
    """True si la requête vise une donnée de marché (prix) sans demande de verdict."""
    if not query or not query.strip():
        return False
    folded = _fold(query)
    if _RECOMMENDATION_HINT.search(folded):
        return False
    return bool(_PRICE_HINT.search(folded))
