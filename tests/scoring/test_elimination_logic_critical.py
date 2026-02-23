"""L3 — Logique d'élimination critique (INV-9, non-optimiste).

Teste l'orchestration de _check_eliminatory_criteria :
  - seuls les critères avec seuil_elimination != None déclenchent une élimination
  - critère non éliminatoire (seuil=None) → ne bloque aucun fournisseur
  - accumulation correcte des éliminations multi-critères
  - isolation : aucun fournisseur actif ne passe à tort

Appel direct à engine._check_eliminatory_criteria (méthode privée).
Justification : méthode pure (zéro DB I/O), isolation maximale sans src/** touches.
Les tests unitaires de _meets_criterion sont dans test_meets_criterion_not_stub.py.
"""

import pytest

from src.core.models import DAOCriterion, SupplierPackage
from src.couche_a.scoring.engine import ScoringEngine

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _supplier(
    name: str = "TEST",
    has_financial: bool = True,
    has_technical: bool = True,
    has_admin: bool = True,
    package_status: str = "COMPLETE",
    missing_fields: list[str] | None = None,
) -> SupplierPackage:
    return SupplierPackage(
        supplier_name=name,
        offer_ids=[],
        documents=[],
        package_status=package_status,
        has_financial=has_financial,
        has_technical=has_technical,
        has_admin=has_admin,
        extracted_data={},
        missing_fields=missing_fields or [],
    )


def _criterion(
    categorie: str,
    seuil: float | None = 50.0,
    nom: str | None = None,
    ordre: int = 1,
) -> DAOCriterion:
    return DAOCriterion(
        categorie=categorie,
        critere_nom=nom or f"Critere-{categorie}",
        description=f"Desc {categorie}",
        ponderation=10.0,
        type_reponse="oui_non",
        seuil_elimination=seuil,
        ordre_affichage=ordre,
    )


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


# ---------------------------------------------------------------------------
# L3a — critère non éliminatoire (seuil=None) → aucune élimination
# ---------------------------------------------------------------------------


def test_l3a_non_eliminatory_criterion_never_eliminates(engine):
    """Critère avec seuil_elimination=None ne doit éliminer aucun fournisseur."""
    suppliers = [_supplier("S1", has_financial=False)]
    criteria = [_criterion("commercial", seuil=None)]

    elims = engine._check_eliminatory_criteria(suppliers, criteria)

    assert elims == [], (
        f"Critère non éliminatoire (seuil=None) ne doit produire aucune élimination, "
        f"obtenu : {elims}"
    )


# ---------------------------------------------------------------------------
# L3b — fournisseur sans doc → éliminé par critère éliminatoire
# ---------------------------------------------------------------------------


def test_l3b_missing_doc_triggers_elimination(engine):
    """Fournisseur sans doc financier + critère commercial éliminatoire → éliminé."""
    suppliers = [_supplier("NO-FIN", has_financial=False)]
    criteria = [_criterion("commercial", seuil=50.0)]

    elims = engine._check_eliminatory_criteria(suppliers, criteria)

    assert len(elims) == 1
    assert elims[0].supplier_name == "NO-FIN"


# ---------------------------------------------------------------------------
# L3c — fournisseur conforme → non éliminé
# ---------------------------------------------------------------------------


def test_l3c_compliant_supplier_not_eliminated(engine):
    """Fournisseur avec tous les docs + critères éliminatoires → aucune élimination."""
    suppliers = [
        _supplier(
            "OK",
            has_financial=True,
            has_technical=True,
            has_admin=True,
            package_status="COMPLETE",
        )
    ]
    criteria = [
        _criterion("commercial", seuil=50.0),
        _criterion("capacity", seuil=50.0),
        _criterion("admin", seuil=50.0),
    ]

    elims = engine._check_eliminatory_criteria(suppliers, criteria)

    assert (
        elims == []
    ), f"Fournisseur conforme ne doit pas être éliminé, obtenu : {elims}"


# ---------------------------------------------------------------------------
# L3d — 2 suppliers, 1 éliminé / 1 passe
# ---------------------------------------------------------------------------


def test_l3d_mixed_suppliers_correct_attribution(engine):
    """2 fournisseurs : l'un éliminé, l'autre passe. Attribution correcte."""
    suppliers = [
        _supplier("NO-TECH", has_technical=False),
        _supplier("OK-TECH", has_technical=True),
    ]
    criteria = [_criterion("capacity", seuil=50.0)]

    elims = engine._check_eliminatory_criteria(suppliers, criteria)

    eliminated_names = {e.supplier_name for e in elims}
    assert "NO-TECH" in eliminated_names
    assert "OK-TECH" not in eliminated_names


# ---------------------------------------------------------------------------
# L3e — aucun critère éliminatoire → aucune élimination
# ---------------------------------------------------------------------------


def test_l3e_no_eliminatory_criteria_no_eliminations(engine):
    """Sans critère éliminatoire, aucun fournisseur ne doit être éliminé."""
    suppliers = [
        _supplier("S1", has_financial=False, has_technical=False),
        _supplier("S2", package_status="PARTIAL"),
    ]
    criteria = [
        _criterion("commercial", seuil=None),
        _criterion("capacity", seuil=None),
    ]

    elims = engine._check_eliminatory_criteria(suppliers, criteria)

    assert (
        elims == []
    ), f"Zéro critère éliminatoire → zéro élimination attendue, obtenu : {elims}"


# ---------------------------------------------------------------------------
# L3f — listes vides → résultat vide
# ---------------------------------------------------------------------------


def test_l3f_empty_inputs_return_empty(engine):
    """Fournisseurs ou critères vides → liste d'éliminations vide."""
    assert engine._check_eliminatory_criteria([], []) == []
    assert engine._check_eliminatory_criteria([_supplier("S1")], []) == []
    assert engine._check_eliminatory_criteria([], [_criterion("commercial")]) == []


# ---------------------------------------------------------------------------
# L3g — essentials : package PARTIAL éliminé, COMPLETE passe
# ---------------------------------------------------------------------------


def test_l3g_essentials_partial_eliminated_complete_passes(engine):
    """Critère 'essentials' éliminatoire : PARTIAL → éliminé, COMPLETE → passe."""
    suppliers = [
        _supplier("PARTIAL-PKG", package_status="PARTIAL"),
        _supplier("COMPLETE-PKG", package_status="COMPLETE", missing_fields=[]),
    ]
    criteria = [_criterion("essentials", seuil=50.0)]

    elims = engine._check_eliminatory_criteria(suppliers, criteria)

    eliminated = {e.supplier_name for e in elims}
    assert "PARTIAL-PKG" in eliminated
    assert "COMPLETE-PKG" not in eliminated


# ---------------------------------------------------------------------------
# L3h — scan anti-régression V-02 : _meets_criterion n'est pas un stub return True
# ---------------------------------------------------------------------------


def test_l3h_antiregression_v02_meets_criterion_not_stub():
    """V-02 : _meets_criterion ne doit pas contenir 'return True' comme seule instruction."""
    from pathlib import Path

    content = Path("src/couche_a/scoring/engine.py").read_text(encoding="utf-8")
    lines = content.splitlines()

    in_fn = False
    body_lines = []
    for line in lines:
        stripped = line.strip()
        if "def _meets_criterion" in stripped:
            in_fn = True
            body_lines = []
            continue
        if in_fn:
            if stripped.startswith("def ") and "def _meets_criterion" not in stripped:
                break
            if stripped:
                body_lines.append(stripped)

    non_doc = [
        ln
        for ln in body_lines
        if not ln.startswith('"""') and not ln.startswith("#") and ln != '"""'
    ]
    assert len(non_doc) > 1, (
        f"_meets_criterion semble être un stub (corps = {non_doc}). "
        "Anti-régression V-02 échoue."
    )
