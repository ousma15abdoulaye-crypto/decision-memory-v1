"""
Mapping zone terrain → code région DMS.

DISCIPLINE DE LECTURE :
  - Une section par région
  - Entrées regroupées sous la bonne section
  - Aucun bloc transversal en fin de fichier
  - Toute nouvelle zone future s'insère dans la section de sa région
    APRÈS validation humaine du mapping
  - Ce fichier ne se "réinvente" jamais à l'intuition

RÈGLE D'AJOUT FUTUR :
  1. Observer la zone réelle dans les données source
  2. Valider humainement son mapping région
  3. L'ajouter dans la section de sa région
  4. Jamais dans un bloc transversal
  5. Jamais sans validation humaine préalable

IMPORTANT :
  Ce fichier contient uniquement les entrées validées probe par probe.
  Il reprend exactement les zones observées et validées CTO.
  Il ne se "corrige" jamais à l'intuition.

Checksum : algorithme maison documenté comme tel.
PAS un Luhn standard — ne pas confondre.
"""

import hashlib

# Tous les codes région valides
ALL_REGION_CODES = {
    "BKO",
    "MPT",
    "SGO",
    "SKS",
    "GAO",
    "TBK",
    "MNK",
    "KYS",
    "KLK",  # RÉSERVÉ · Kidal · aucune zone mappée en M4 · activation mandat CTO requis
    "INT",  # RÉSERVÉ · International · aucune zone mappée en M4 · activation mandat CTO requis
}

ZONE_TO_REGION: dict[str, str] = {
    # ── BAMAKO ───────────────────────────────────────────────
    # Probe B0.5 · 2026-03-01
    "bamako": "BKO",
    "kati": "BKO",
    "koulikoro": "BKO",
    # Probe PATCH-B · 2026-03-02 · Option A validée CTO
    "sans fil": "BKO",
    "siby": "BKO",
    # ── GAO ──────────────────────────────────────────────────
    # Probe B0.5 · 2026-03-01
    "gao": "GAO",
    "ansongo": "GAO",
    "bourem": "GAO",
    # ── KAYES ────────────────────────────────────────────────
    # Probe B0.5 · 2026-03-01
    "kayes": "KYS",
    # ── MÉNAKA ───────────────────────────────────────────────
    # Probe B0.5 · 2026-03-01
    "menaka": "MNK",
    # ── MOPTI ────────────────────────────────────────────────
    # Probe B0.5 · 2026-03-01
    "mopti": "MPT",
    "sevare": "MPT",
    "douentza": "MPT",
    "bandiagara": "MPT",
    "bankass": "MPT",
    "koro": "MPT",
    "djenne": "MPT",
    "tenenkou": "MPT",
    "youwarou": "MPT",
    # Probe PATCH-B · 2026-03-02 · Option A validée CTO
    "sevare - mopti": "MPT",
    # ── SÉGOU ────────────────────────────────────────────────
    # Probe B0.5 · 2026-03-01
    "segou": "SGO",
    "san": "SGO",
    "bla": "SGO",
    # Probe PATCH-B · 2026-03-02 · Option A validée CTO
    "angouleme segou": "SGO",
    "hamdallaye segou": "SGO",
    # ── SIKASSO ──────────────────────────────────────────────
    # Probe B0.5 · 2026-03-01
    "sikasso": "SKS",
    "bougouni": "SKS",
    "koutiala": "SKS",
    "kadiolo": "SKS",
    # Probe PATCH-B · 2026-03-02 · Option A validée CTO
    "niena": "SKS",
    "sikasso medine": "SKS",
    # ── TOMBOUCTOU ───────────────────────────────────────────
    # Probe B0.5 · 2026-03-01
    "niafunke": "TBK",
    "tombouctou": "TBK",
    "dire": "TBK",
    "goundam": "TBK",
    "rharous": "TBK",
    "gourma rharous": "TBK",
}

_DMS_SALT = "DMS-SALT-MALI-2026-V1"
_CHK_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # sans I et O


def _checksum_char(base: str) -> str:
    """Caractère de contrôle — checksum maison · pas un Luhn standard."""
    digest = hashlib.sha256(f"{base}-{_DMS_SALT}".encode()).hexdigest()
    idx = int(digest[:8], 16) % len(_CHK_ALPHABET)
    return _CHK_ALPHABET[idx]


def build_vendor_id(region_code: str, sequence: int) -> str:
    """
    Construit le DMS_VENDOR_ID.
    Appelé uniquement depuis repository.insert_vendor().
    Jamais depuis un DataFrame ETL.

    Format : DMS-VND-{REGION}-{SEQ:04d}-{CHK}
    Exemple : DMS-VND-BKO-0001-K

    Args:
        region_code : code 3 lettres validé dans ALL_REGION_CODES
        sequence    : entier >= 1 · fourni par get_next_sequence()
    """
    if region_code not in ALL_REGION_CODES:
        raise ValueError(f"region_code invalide : {region_code!r}")
    if sequence < 1:
        raise ValueError(f"sequence doit être >= 1 · reçu : {sequence}")
    base = f"DMS-VND-{region_code}-{sequence:04d}"
    return f"{base}-{_checksum_char(base)}"
