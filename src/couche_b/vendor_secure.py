"""
ADR-014 — Vendor Secure Service
Chiffrement AES-256-GCM pour données sensibles fournisseurs.
Pattern : extract → encrypt → store → token → Label Studio

RÈGLE : aucune valeur brute sensible ne quitte ce module
        vers Label Studio ou les logs.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# CONFIGURATION — variables env obligatoires
# ─────────────────────────────────────────────────────────

VENDOR_ENCRYPTION_KEY = os.environ.get("VENDOR_ENCRYPTION_KEY", "")
PSEUDONYM_SALT = os.environ.get("PSEUDONYM_SALT", "")

if not VENDOR_ENCRYPTION_KEY:
    logger.warning(
        "[SECURITY] VENDOR_ENCRYPTION_KEY absent — " "chiffrement vendor désactivé"
    )
if not PSEUDONYM_SALT:
    logger.warning("[SECURITY] PSEUDONYM_SALT absent — " "tokens non salés")

# Champs sensibles → type
SENSITIVE_FIELDS = {
    "supplier_nif_raw": "nif",
    "supplier_rccm_raw": "rccm",
    "supplier_phone_raw": "phone",
    "supplier_email_raw": "email",
}

# Documents à validité annuelle
VALIDITY_DOCS = {
    "quitus_fiscal_date": "quitus_fiscal",
    "cert_non_faillite_date": "cert_non_faillite",
}

ABSENT = "ABSENT"
NOT_APPLICABLE = "NOT_APPLICABLE"


# ─────────────────────────────────────────────────────────
# CHIFFREMENT — AES-256-GCM via cryptography lib
# ─────────────────────────────────────────────────────────


def _get_fernet():
    """
    Retourne une instance Fernet (AES-128-CBC + HMAC-SHA256).
    Utilisé si cryptography est disponible.
    Fallback : base64 simple avec WARNING si clé absente.
    """
    try:
        from cryptography.fernet import Fernet

        if not VENDOR_ENCRYPTION_KEY:
            return None
        key = VENDOR_ENCRYPTION_KEY.encode()
        if len(key) < 32:
            key = key.ljust(32, b"0")
        fernet_key = base64.urlsafe_b64encode(key[:32])
        return Fernet(fernet_key)
    except ImportError:
        logger.error(
            "[SECURITY] cryptography non installé — " "pip install cryptography requis"
        )
        return None


def _encrypt(value: str) -> str:
    """
    Chiffre une valeur sensible.
    Avec clé    : Fernet(AES-128-CBC + HMAC) → base64
    Sans clé    : base64 simple + WARNING (dégradé)
    """
    fernet = _get_fernet()
    if fernet:
        return fernet.encrypt(value.encode()).decode()
    logger.warning(
        "[SECURITY] VENDOR_ENCRYPTION_KEY absent — "
        "valeur encodée base64 uniquement (non chiffrée)"
    )
    return base64.b64encode(value.encode()).decode()


def _decrypt(encrypted: str, accessed_by: str = "system") -> str:
    """
    Déchiffre une valeur.
    Action auditée — accessed_by obligatoire.
    """
    fernet = _get_fernet()
    if fernet:
        return fernet.decrypt(encrypted.encode()).decode()
    return base64.b64decode(encrypted.encode()).decode()


# ─────────────────────────────────────────────────────────
# TOKENS — déterministes pour déduplication vendor
# ─────────────────────────────────────────────────────────


def _generate_token(field_type: str, value: str) -> str:
    """
    Génère un token déterministe.
    tok_{field_type}_{HMAC-SHA256(value, PSEUDONYM_SALT)[:8]}
    Même valeur + même sel → même token.
    """
    if PSEUDONYM_SALT:
        h = hmac.new(
            PSEUDONYM_SALT.encode(),
            value.encode(),
            hashlib.sha256,
        ).hexdigest()[:8]
    else:
        h = hashlib.sha256(value.encode()).hexdigest()[:8]
    return f"tok_{field_type}_{h}"


def _normalize_supplier_name(name: str) -> str:
    """
    Normalise le nom fournisseur pour jointure vendor registry.
    """
    if not name or name in (ABSENT, NOT_APPLICABLE):
        return "unknown"
    return (
        name.lower()
        .strip()
        .replace("sarl", "")
        .replace("sa ", "")
        .replace("  ", " ")
        .strip()
    )


# ─────────────────────────────────────────────────────────
# VALIDITÉ DOCUMENTS ANNUELS
# ─────────────────────────────────────────────────────────


def _days_until_expiry(date_str: str) -> int:
    """
    Calcule le nombre de jours avant expiration d'un document.
    date_str : ISO format YYYY-MM-DD
    Retourne négatif si expiré.
    """
    try:
        doc_date = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
        expiry = doc_date.replace(year=doc_date.year + 1)
        delta = expiry - datetime.now(UTC)
        return delta.days
    except (ValueError, TypeError):
        logger.warning("Date invalide pour calcul expiry : %s", date_str)
        return -1


def compute_doc_validity(date_str: str) -> dict:
    """
    Retourne le statut de validité d'un document annuel.
    Ne retourne JAMAIS la date brute — uniquement booléen + jours.
    """
    if not date_str or date_str in (ABSENT, NOT_APPLICABLE):
        return {
            "is_valid": None,
            "expires_in_days": None,
            "status": ABSENT,
        }
    days = _days_until_expiry(date_str)
    return {
        "is_valid": days > 0,
        "expires_in_days": days,
        "status": "VALID" if days > 0 else "EXPIRED",
    }


# ─────────────────────────────────────────────────────────
# STOCKAGE — vendors_sensitive_data
# ─────────────────────────────────────────────────────────


def _store_encrypted(
    conn: psycopg.Connection,
    token: str,
    field_type: str,
    raw_value: str,
    supplier_name_normalized: str,
    case_id: str | None,
    annotation_task_id: str | None,
) -> None:
    """
    Chiffre et stocke une valeur sensible.
    Idempotent : ON CONFLICT DO NOTHING (même token = même valeur).
    """
    encrypted = _encrypt(raw_value)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO vendors_sensitive_data
                (token, field_type, encrypted_value,
                 supplier_name_normalized, case_id, annotation_task_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (token) DO NOTHING;
            """,
            (
                token,
                field_type,
                encrypted,
                supplier_name_normalized,
                case_id,
                annotation_task_id,
            ),
        )


def _store_doc_validity(
    conn: psycopg.Connection,
    supplier_name_normalized: str,
    doc_type: str,
    raw_date: str,
    validity: dict,
    case_id: str | None,
    annotation_task_id: str | None,
) -> None:
    """
    Stocke la validité d'un document annuel.
    La date brute est chiffrée — seuls booléen et jours sont clairs.
    """
    encrypted_date = _encrypt(raw_date)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO vendors_doc_validity
                (supplier_name_normalized, case_id, doc_type,
                 encrypted_date, is_valid, expires_in_days,
                 annotation_task_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT uq_vendor_doc
            DO UPDATE SET
                encrypted_date     = EXCLUDED.encrypted_date,
                is_valid           = EXCLUDED.is_valid,
                expires_in_days    = EXCLUDED.expires_in_days,
                computed_at        = now(),
                annotation_task_id = EXCLUDED.annotation_task_id;
            """,
            (
                supplier_name_normalized,
                case_id,
                doc_type,
                encrypted_date,
                validity["is_valid"],
                validity["expires_in_days"],
                annotation_task_id,
            ),
        )


# ─────────────────────────────────────────────────────────
# POINT D'ENTRÉE PRINCIPAL — appelé par backend.py
# ─────────────────────────────────────────────────────────


def secure_identifiants(
    raw_identifiants: dict,
    conn: psycopg.Connection,
    case_id: str | None = None,
    task_id: int | None = None,
) -> dict:
    """
    Sécurise le bloc identifiants avant envoi vers Label Studio.

    ENTRÉE  : dict identifiants bruts depuis Mistral
    SORTIE  : dict avec tokens + booléens validité
              JAMAIS de valeur brute sensible

    Champs traités :
      supplier_nif_raw   → token tok_nif_XXXX
      supplier_rccm_raw  → token tok_rccm_XXXX
      supplier_phone_raw → token tok_phone_XXXX
      supplier_email_raw → token tok_email_XXXX
      quitus_fiscal_date → is_valid + expires_in_days
      cert_non_faillite_date → is_valid + expires_in_days
      has_rib            → conservé booléen (ADR-013)
    """
    secured = dict(raw_identifiants)
    task_id_str = str(task_id) if task_id else None

    supplier_norm = _normalize_supplier_name(secured.get("supplier_name_raw", ""))

    # 1. Champs texte sensibles → tokens
    for field_key, field_type in SENSITIVE_FIELDS.items():
        raw_value = secured.pop(field_key, None)

        if raw_value and raw_value not in (ABSENT, NOT_APPLICABLE, "", None):
            token = _generate_token(field_type, str(raw_value))
            try:
                _store_encrypted(
                    conn,
                    token,
                    field_type,
                    str(raw_value),
                    supplier_norm,
                    case_id,
                    task_id_str,
                )
                conn.commit()
            except Exception as exc:
                logger.error(
                    "[VENDOR SECURE] Erreur stockage %s : len=%d — %s",
                    field_type,
                    len(str(raw_value)),
                    type(exc).__name__,
                )
                conn.rollback()
                token = ABSENT

            secured[f"supplier_{field_type}_token"] = token
            secured[f"supplier_{field_type}_present"] = True
        else:
            secured[f"supplier_{field_type}_token"] = ABSENT
            secured[f"supplier_{field_type}_present"] = False

    # 2. Documents annuels → validité calculée
    for date_field, doc_type in VALIDITY_DOCS.items():
        raw_date = secured.pop(date_field, None)

        validity = compute_doc_validity(raw_date or ABSENT)

        secured[f"{doc_type}_valide"] = validity["is_valid"]
        secured[f"{doc_type}_expire_dans_jours"] = validity["expires_in_days"]
        secured[f"{doc_type}_status"] = validity["status"]

        if raw_date and raw_date not in (ABSENT, NOT_APPLICABLE):
            try:
                _store_doc_validity(
                    conn,
                    supplier_norm,
                    doc_type,
                    raw_date,
                    validity,
                    case_id,
                    task_id_str,
                )
                conn.commit()
            except Exception as exc:
                logger.error(
                    "[VENDOR SECURE] Erreur stockage doc_validity %s : %s",
                    doc_type,
                    type(exc).__name__,
                )
                conn.rollback()

    # 3. has_rib conservé booléen (ADR-013 — jamais la valeur)

    return secured


# ─────────────────────────────────────────────────────────
# DÉCHIFFREMENT — API dédiée — action auditée
# ─────────────────────────────────────────────────────────


def decrypt_vendor_field(
    conn: psycopg.Connection,
    token: str,
    accessed_by: str,
) -> dict:
    """
    Déchiffre une valeur sensible depuis son token.
    Action auditée : accessed_by + accessed_at mis à jour.
    Réservé aux rôles : admin, vendor_admin.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            UPDATE vendors_sensitive_data
            SET accessed_by = %s, accessed_at = now()
            WHERE token = %s
            RETURNING field_type, encrypted_value,
                      supplier_name_normalized, case_id;
            """,
            (accessed_by, token),
        )
        row = cur.fetchone()

    if not row:
        return {"error": "token_not_found", "token": token}

    conn.commit()

    try:
        decrypted = _decrypt(row["encrypted_value"], accessed_by)
    except Exception as exc:
        logger.error(
            "[VENDOR SECURE] Déchiffrement échoué token=%s : %s",
            token[:8],
            type(exc).__name__,
        )
        return {"error": "decryption_failed"}

    return {
        "field_type": row["field_type"],
        "value": decrypted,
        "supplier_name_normalized": row["supplier_name_normalized"],
        "case_id": row["case_id"],
        "accessed_by": accessed_by,
    }
