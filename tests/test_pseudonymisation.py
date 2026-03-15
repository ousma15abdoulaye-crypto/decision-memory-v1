"""
Tests pseudonymisation phone/email — backend annotation
ADR-013 · RÈGLE-SEC-1

Couvre (per review comment 2937042508) :
  - sel présent vs absent (_pseudonymise)
  - valeurs sentinelles ABSENT / NOT_APPLICABLE / AMBIGUOUS
  - supplier_phone_raw / supplier_email_raw ne sortent jamais en clair
    dans extracted_json (_build_ls_result)

Ces tests sont purement unitaires — aucune connexion DB requise.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import importlib.util
import json
import os

import pytest

# ─────────────────────────────────────────────────────────
# Chargement du module avec les variables d'env requises
# ─────────────────────────────────────────────────────────

_BACKEND_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "services",
    "annotation-backend",
    "backend.py",
)

# Positionner les variables AVANT le chargement du module
# (le module lève RuntimeError à l'import si PSEUDONYM_SALT absent
# et ALLOW_WEAK_PSEUDONYMIZATION non activé)
os.environ.setdefault("PSEUDONYM_SALT", "test-sel-adr013-pytest")
os.environ.setdefault("ALLOW_WEAK_PSEUDONYMIZATION", "1")
# MISTRAL_API_KEY non requis — le module le rend optionnel
os.environ.setdefault("MISTRAL_API_KEY", "")

_spec = importlib.util.spec_from_file_location("_backend_annot", _BACKEND_PATH)
_backend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_backend)

_pseudonymise = _backend._pseudonymise
_pseudonymise_contact = _backend._pseudonymise_contact
_build_ls_result = _backend._build_ls_result
ABSENT = _backend.ABSENT
NOT_APPLICABLE = _backend.NOT_APPLICABLE


# ─────────────────────────────────────────────────────────
# _pseudonymise — sel présent vs absent
# ─────────────────────────────────────────────────────────


def test_pseudonymise_avec_sel_retourne_hmac(monkeypatch):
    """Avec sel : résultat = HMAC-SHA256(value, sel)[:16]."""
    monkeypatch.setattr(_backend, "PSEUDONYM_SALT", "mon-sel-secret")
    value = "+223 76 00 00 01"
    expected = hmac.new(
        b"mon-sel-secret",
        value.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    assert _pseudonymise(value) == expected


def test_pseudonymise_sans_sel_retourne_sha256(monkeypatch):
    """Sans sel : résultat = SHA256(value)[:16] (mode dégradé)."""
    monkeypatch.setattr(_backend, "PSEUDONYM_SALT", "")
    value = "+223 76 00 00 01"
    expected = hashlib.sha256(value.encode()).hexdigest()[:16]
    assert _pseudonymise(value) == expected


def test_pseudonymise_sel_different_donne_hash_different(monkeypatch):
    """Deux sels différents → deux hashes différents (isolation projet)."""
    value = "contact@example.com"
    monkeypatch.setattr(_backend, "PSEUDONYM_SALT", "sel-A")
    h1 = _pseudonymise(value)
    monkeypatch.setattr(_backend, "PSEUDONYM_SALT", "sel-B")
    h2 = _pseudonymise(value)
    assert h1 != h2


def test_pseudonymise_retourne_16_chars():
    """Le hash retourné fait exactement 16 caractères."""
    assert len(_pseudonymise("quelque-chose")) == 16


# ─────────────────────────────────────────────────────────
# _pseudonymise_contact — valeurs sentinelles
# ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "valeur_sentinelle",
    [
        ABSENT,
        NOT_APPLICABLE,
        "AMBIGUOUS",
        "",
        None,
    ],
)
def test_pseudonymise_contact_sentinelle_retourne_present_false(valeur_sentinelle):
    """
    Valeurs ABSENT / NOT_APPLICABLE / AMBIGUOUS / vide / None
    → present=False, pseudo=None, redacted=False.
    """
    bloc = _pseudonymise_contact(valeur_sentinelle)
    assert bloc["present"] is False
    assert bloc["pseudo"] is None
    assert bloc["redacted"] is False


def test_pseudonymise_contact_valeur_reelle_retourne_present_true():
    """Valeur réelle → present=True, redacted=True, pseudo = 16 chars hex."""
    bloc = _pseudonymise_contact("+223 76 12 34 56")
    assert bloc["present"] is True
    assert bloc["redacted"] is True
    assert bloc["pseudo"] is not None
    assert len(bloc["pseudo"]) == 16


def test_pseudonymise_contact_meme_valeur_donne_meme_pseudo():
    """Déterminisme : même valeur → même pseudo."""
    v = "test@example.org"
    assert _pseudonymise_contact(v)["pseudo"] == _pseudonymise_contact(v)["pseudo"]


def test_pseudonymise_contact_valeurs_differentes_donnent_pseudos_differents():
    """Deux valeurs distinctes → deux pseudos distincts."""
    b1 = _pseudonymise_contact("+223 76 00 00 01")
    b2 = _pseudonymise_contact("+223 76 00 00 02")
    assert b1["pseudo"] != b2["pseudo"]


# ─────────────────────────────────────────────────────────
# _build_ls_result — supplier_phone_raw / email_raw hors extracted_json
# ─────────────────────────────────────────────────────────

_PARSED_MINIMAL = {
    "couche_1_routing": {
        "procurement_family_main": "goods",
        "procurement_family_sub": "food",
        "taxonomy_core": "rfq",
        "document_role": "offer_financial",
        "document_stage": "solicitation",
    },
    "couche_5_gates": [],
    "ambiguites": [],
    "_meta": {
        "review_required": False,
        "mistral_model_used": "mistral-small-latest",
    },
    "identifiants": {
        "supplier_name_raw": "Fournisseur SARL",
        "supplier_name_normalized": "fournisseur-sarl",
        "supplier_identifier_raw": ABSENT,
        "supplier_legal_form": ABSENT,
        "supplier_address_raw": ABSENT,
        "supplier_phone_raw": "+223 76 99 88 77",
        "supplier_email_raw": "fournisseur@example.ml",
        "case_id": ABSENT,
        "supplier_id": NOT_APPLICABLE,
        "lot_scope": [],
        "zone_scope": [],
    },
}


def test_build_ls_result_phone_raw_absent_du_json():
    """supplier_phone_raw ne doit jamais apparaître dans extracted_json."""
    result = _build_ls_result(_PARSED_MINIMAL, task_id=1)
    extracted = result[0]["value"]["text"][0]
    assert "supplier_phone_raw" not in extracted


def test_build_ls_result_email_raw_absent_du_json():
    """supplier_email_raw ne doit jamais apparaître dans extracted_json."""
    result = _build_ls_result(_PARSED_MINIMAL, task_id=1)
    extracted = result[0]["value"]["text"][0]
    assert "supplier_email_raw" not in extracted


def test_build_ls_result_valeur_phone_en_clair_absente_du_json():
    """La valeur brute du téléphone ne doit pas figurer dans extracted_json."""
    result = _build_ls_result(_PARSED_MINIMAL, task_id=1)
    extracted = result[0]["value"]["text"][0]
    assert "+223 76 99 88 77" not in extracted


def test_build_ls_result_valeur_email_en_clair_absente_du_json():
    """La valeur brute de l'email ne doit pas figurer dans extracted_json."""
    result = _build_ls_result(_PARSED_MINIMAL, task_id=1)
    extracted = result[0]["value"]["text"][0]
    assert "fournisseur@example.ml" not in extracted


def test_build_ls_result_supplier_phone_pseudo_present_dans_json():
    """supplier_phone pseudo-bloc (present=True) figure dans extracted_json."""
    result = _build_ls_result(_PARSED_MINIMAL, task_id=1)
    extracted_obj = json.loads(result[0]["value"]["text"][0])
    phone_bloc = extracted_obj["identifiants"]["supplier_phone"]
    assert phone_bloc["present"] is True
    assert phone_bloc["redacted"] is True
    assert len(phone_bloc["pseudo"]) == 16


def test_build_ls_result_supplier_email_pseudo_present_dans_json():
    """supplier_email pseudo-bloc (present=True) figure dans extracted_json."""
    result = _build_ls_result(_PARSED_MINIMAL, task_id=1)
    extracted_obj = json.loads(result[0]["value"]["text"][0])
    email_bloc = extracted_obj["identifiants"]["supplier_email"]
    assert email_bloc["present"] is True
    assert email_bloc["redacted"] is True
    assert len(email_bloc["pseudo"]) == 16


def test_build_ls_result_sentinelles_donnent_present_false():
    """Valeurs ABSENT en entrée → supplier_phone/email present=False dans JSON."""
    parsed = {
        **_PARSED_MINIMAL,
        "identifiants": {
            **_PARSED_MINIMAL["identifiants"],
            "supplier_phone_raw": ABSENT,
            "supplier_email_raw": NOT_APPLICABLE,
        },
    }
    result = _build_ls_result(parsed, task_id=2)
    extracted_obj = json.loads(result[0]["value"]["text"][0])
    assert extracted_obj["identifiants"]["supplier_phone"]["present"] is False
    assert extracted_obj["identifiants"]["supplier_email"]["present"] is False


def test_build_ls_result_ne_modifie_pas_le_parsed_original():
    """_build_ls_result opère sur une copie — le dict d'entrée est inchangé."""
    original = copy.deepcopy(_PARSED_MINIMAL)
    _build_ls_result(_PARSED_MINIMAL, task_id=3)
    assert _PARSED_MINIMAL["identifiants"] == original["identifiants"]
