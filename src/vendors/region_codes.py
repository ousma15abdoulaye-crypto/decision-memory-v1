"""
Mapping zone normalisée → code région DMS.

ZONE_TO_REGION est construit depuis les données réelles observées
lors du probe B0.5 (2026-03-01) et étendu lors du probe PATCH-B (2026-03-02).

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
    "KLK",
    "INT",
}

# Mapping zone normalisée → region_code
# Construit depuis le réel observé · probe B0.5 · 2026-03-01
# Zones observées dans les fichiers : BAMAKO, MOPTI, SEVARE, BANDIAGARA,
# BANKASS, DJENNE, DOUENTZA, GAO, NIAFUNKE, TOMBOUCTOU
ZONE_TO_REGION: dict[str, str] = {
    # ── Bamako ────────────────────────────────────────
    "bamako": "BKO",
    "kati": "BKO",
    "koulikoro": "BKO",
    # ── Mopti ─────────────────────────────────────────
    "mopti": "MPT",
    "sevare": "MPT",
    "douentza": "MPT",
    "bandiagara": "MPT",
    "bankass": "MPT",
    "koro": "MPT",
    "djenne": "MPT",
    "tenenkou": "MPT",
    "youwarou": "MPT",
    # ── Tombouctou ────────────────────────────────────
    "niafunke": "TBK",
    "tombouctou": "TBK",
    "dire": "TBK",
    "goundam": "TBK",
    "rharous": "TBK",
    "gourma rharous": "TBK",
    # ── Gao ───────────────────────────────────────────
    "gao": "GAO",
    "ansongo": "GAO",
    "bourem": "GAO",
    # ── Ménaka ────────────────────────────────────────
    "menaka": "MNK",
    # ── Ségou ─────────────────────────────────────────
    "segou": "SGO",
    "san": "SGO",
    "bla": "SGO",
    # ── Sikasso ───────────────────────────────────────
    "sikasso": "SKS",
    "bougouni": "SKS",
    "koutiala": "SKS",
    "kadiolo": "SKS",
    # ── Kayes ─────────────────────────────────────────
    "kayes": "KYS",
    # ── Zones ajoutées PATCH-B · probe 2026-03-02 (Option A) ──
    # Ségou — quartiers et sous-zones
    "angouleme segou": "SGO",
    "hamdallaye segou": "SGO",
    # Sikasso — quartiers et sous-zones
    "niena": "SKS",
    "sikasso medine": "SKS",
    # Bamako — quartiers et communes périphériques
    "sans fil": "BKO",
    "siby": "BKO",
    # Mopti — variante orthographique avec tiret
    "sevare - mopti": "MPT",
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
