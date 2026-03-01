"""
Normalisation données fournisseurs Mali.

Source de vérité unique pour zone_normalized.
Pas de GENERATED COLUMN DB — ce fichier fait foi.
"""

import re
import unicodedata

_PLACEHOLDER_EMAILS = {
    "tobecomplete@savethechildren.org",
    "tobecompleted@savethechildren.org",
    "dummy@gmail.com",
    "dummy@gmail.fr",
    "0",
}

_INVALID_PHONES = {"0", "", "00"}


def normalize_text(s: str | None) -> str:
    """Minuscules · sans accents · sans espaces multiples."""
    if not s or str(s).strip() in ("", "nan"):
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


def normalize_zone(s: str | None) -> str:
    """
    Normalise une zone pour lookup dans ZONE_TO_REGION.
    Source de vérité : cette fonction · pas unaccent() SQL.
    """
    if not s:
        return ""
    result = normalize_text(s)
    result = re.sub(r"\s*\(.*?\)", "", result).strip()
    return result


def normalize_name(s: str | None) -> str | None:
    if not s or str(s).strip() in ("", "nan"):
        return None
    return re.sub(r"\s+", " ", str(s).strip())


def normalize_email(s: str | None) -> str | None:
    if not s:
        return None
    email = str(s).strip().lower()
    if email in _PLACEHOLDER_EMAILS:
        return None
    for placeholder in _PLACEHOLDER_EMAILS:
        if placeholder in email:
            return None
    if "@" not in email or "." not in email.split("@")[-1]:
        return None
    return email


def normalize_phone(s: str | None) -> str | None:
    if not s:
        return None
    phone = re.sub(r"[\s\-\.\(\)\+]", "", str(s))
    if phone in _INVALID_PHONES:
        return None
    phone = re.sub(r"\D", "", phone)
    if len(phone) < 7:
        return None
    if phone.startswith("223") and len(phone) == 11:
        phone = phone[3:]
    return phone or None
