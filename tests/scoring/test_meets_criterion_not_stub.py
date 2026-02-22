"""
L4 — Gate anti-stub : _meets_criterion doit être une vraie implémentation.

INV-9 : zéro hypothèse silencieuse, zéro élimination fantôme.
Basé sur la structure prouvée Étape 0 :
  - criterion: DAOCriterion (categorie, seuil_elimination: float|None, ...)
  - supplier: SupplierPackage (has_financial, has_technical, has_admin,
                               package_status, missing_fields)
"""

from pathlib import Path

from src.core.models import DAOCriterion, SupplierPackage

ENGINE_PATH = Path("src/couche_a/scoring/engine.py")


def _engine_content() -> str:
    assert ENGINE_PATH.exists(), f"{ENGINE_PATH} introuvable"
    return ENGINE_PATH.read_text(encoding="utf-8")


# --- Static gates ---


def test_no_stub_comment_in_meets_criterion():
    """Aucun commentaire stub autour de _meets_criterion."""
    content = _engine_content()
    forbidden = [
        "assume all suppliers",
        "For now",
        "TODO",
    ]
    for phrase in forbidden:
        assert phrase not in content, (
            f"Stub phrase '{phrase}' encore présente dans {ENGINE_PATH}. "
            "_meets_criterion doit être une vraie implémentation."
        )


def test_return_true_only_in_non_eliminatory_branch():
    """'return True' isolé ne doit pas être la seule ligne du corps de _meets_criterion."""
    content = _engine_content()
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
        "_meets_criterion semble être un stub : corps vide ou 'return True' unique. "
        f"Corps détecté : {non_doc}"
    )


# --- Behaviour tests (structure réelle prouvée Étape 0) ---


def _make_supplier(**kwargs) -> SupplierPackage:
    defaults = dict(
        supplier_name="TestSupplier",
        offer_ids=[],
        documents=[],
        package_status="PARTIAL",
        has_financial=False,
        has_technical=False,
        has_admin=False,
        extracted_data={},
        missing_fields=["financial_doc"],
    )
    defaults.update(kwargs)
    return SupplierPackage(**defaults)


def _make_criterion(categorie: str, seuil: float = 50.0) -> DAOCriterion:
    return DAOCriterion(
        categorie=categorie,
        critere_nom=f"Critere {categorie}",
        description=f"Description {categorie}",
        ponderation=10.0,
        type_reponse="oui_non",
        seuil_elimination=seuil,
        ordre_affichage=1,
    )


def _engine():
    from src.couche_a.scoring.engine import ScoringEngine

    return ScoringEngine()


def test_commercial_criterion_without_financial_doc_eliminates():
    """Fournisseur sans doc financier → éliminé sur critère commercial."""
    engine = _engine()
    supplier = _make_supplier(has_financial=False)
    criterion = _make_criterion("commercial")
    assert engine._meets_criterion(supplier, criterion) is False


def test_commercial_criterion_with_financial_doc_passes():
    """Fournisseur avec doc financier → passe le critère commercial."""
    engine = _engine()
    supplier = _make_supplier(has_financial=True)
    criterion = _make_criterion("commercial")
    assert engine._meets_criterion(supplier, criterion) is True


def test_capacity_criterion_without_technical_doc_eliminates():
    """Fournisseur sans doc technique → éliminé sur critère capacity."""
    engine = _engine()
    supplier = _make_supplier(has_technical=False)
    criterion = _make_criterion("capacity")
    assert engine._meets_criterion(supplier, criterion) is False


def test_essentials_criterion_incomplete_package_eliminates():
    """Package PARTIAL → éliminé sur critère essentials."""
    engine = _engine()
    supplier = _make_supplier(package_status="PARTIAL")
    criterion = _make_criterion("essentials")
    assert engine._meets_criterion(supplier, criterion) is False


def test_essentials_criterion_complete_package_passes():
    """Package COMPLETE → passe le critère essentials."""
    engine = _engine()
    supplier = _make_supplier(package_status="COMPLETE", missing_fields=[])
    criterion = _make_criterion("essentials")
    assert engine._meets_criterion(supplier, criterion) is True


def test_unknown_category_with_missing_fields_eliminates():
    """Catégorie inconnue + champs manquants → élimination défensive."""
    engine = _engine()
    supplier = _make_supplier(missing_fields=["doc_x"])
    criterion = _make_criterion("autre_categorie_inconnue")
    assert engine._meets_criterion(supplier, criterion) is False
