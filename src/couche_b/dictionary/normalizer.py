"""
src/couche_b/dictionary/normalizer.py

Normaliseur libellés procurement DMS.
Déterministe · idempotent · local · zéro LLM.
Miroir Python de unaccent(lower()) PostgreSQL.
Arabe hors scope (décision CTO).

RÈGLE-33 étendue :
  geo/normalizer.py      → noms géographiques
  dictionary/normalizer.py → libellés procurement
"""

from __future__ import annotations
import hashlib
import re
import unicodedata
from functools import lru_cache


# ----------------------------------------------------------------
# STOPWORDS · dédupliqués · sans unités
# ----------------------------------------------------------------
_STOPWORDS = frozenset({
    "de", "du", "des", "le", "la", "les", "l", "d",
    "en", "par", "pour", "sur", "avec", "sans", "a",
    "au", "aux", "et", "ou", "un", "une",
    "type", "qualite", "standard", "ordinaire",
    "courant", "neuf", "local", "importe",
})

# ----------------------------------------------------------------
# ABRÉVIATIONS TERRAIN · clés = déjà normalisées NFD+lower
# ----------------------------------------------------------------
_ABBREVIATIONS: dict[str, str] = {
    # Liants
    "cmt":        "ciment",
    "portland":   "ciment_portland",
    "cem":        "ciment_cem",
    # Aciers (ha gardé tel quel · "fer ha" → fer_ha via tokenisation)
    "tor":        "fer_tor",
    "rond":       "fer_rond",
    # Maçonnerie
    "agglo":      "agglomere",
    "agglos":     "agglomere",
    "parpaing":   "agglomere",
    # Couverture
    "galva":      "galvanise",
    # Emballages
    "bag":        "sac",
    "fut":        "fut",
    "fût":        "fut",
    # Abréviations anglais technique limité
    "pl":         "planche",
}

_UNITS = frozenset({
    "kg", "g", "t", "tonne",
    "m", "ml", "m2", "m3",
    "l", "litre", "cl",
    "mm", "cm",
    "piece", "pce", "unite",
    "sac", "bag", "rouleau",
    "barre", "feuille", "fut",
    "bidon", "boite", "paquet",
    "litre", "sac_50kg",
    "comprime", "flacon",
    "voyage", "heure",
})


@lru_cache(maxsize=16384)
def normalize_label(raw: str) -> str:
    """
    Normalise un libellé procurement → slug stable.
    Déterministe · idempotent · cachée lru_cache(16384).

    Exemples :
      'Ciment Portland 50kg'  → 'ciment_portland_50kg'
      'FER HA 10mm'           → 'fer_ha_10mm'
      'Tôle ondulée 0,4mm'    → 'tole_ondulee_04mm'
      'gasoil'                → 'gasoil'
      'ciment CPA 42.5'       → 'ciment_cpa_42.5'
    """
    if not raw or not raw.strip():
        return ""

    # 1. NFD + suppression diacritiques (miroir unaccent SQL)
    nfd  = unicodedata.normalize("NFD", raw.strip())
    text = "".join(
        c for c in nfd
        if unicodedata.category(c) != "Mn"
    )

    # 2. Lowercase
    text = text.lower()

    # 3. Séparateurs → espace
    text = re.sub(r"[/\\|;:'\"\(\)]", " ", text)

    # 4. Virgule décimale → point (12,5 → 12.5)
    text = re.sub(r"(\d),(\d)", r"\1.\2", text)

    # 5. Coller nombre + unité (50 kg → 50kg)
    text = re.sub(
        r"(\d+)\s*(kg|g|mm|cm|m2|m3|ml|l|t)\b",
        r"\1\2", text,
    )

    # 6. Tokenisation
    tokens = text.split()

    # 7. Abréviations
    tokens = [_ABBREVIATIONS.get(t, t) for t in tokens]

    # 8. Suppression stopwords
    #    Exception : tokens numériques et unités conservés
    tokens = [
        t for t in tokens
        if t not in _STOPWORDS
        or bool(re.match(r"^\d", t))
        or t in _UNITS
    ]

    if not tokens:
        return ""

    # 9. Jointure underscore + nettoyage
    slug = "_".join(tokens)
    return re.sub(r"_+", "_", slug).strip("_")


def build_canonical_slug(raw: str) -> str:
    """Alias sémantique · clarté du code."""
    return normalize_label(raw)


def generate_deterministic_id(slug: str, prefix: str = "di") -> str:
    """
    ID déterministe SHA256(slug)[:16].
    Idempotent · même slug → même id · DÉCISION-M6-04.

    Préfixes :
      di  → dict_items (procurement_dict_items)
      da  → dict_aliases
      dp  → dict_proposals
      dcl → dict_collision_log
    """
    h = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{h}"
