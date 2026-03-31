"""
Tests M12 LLM Arbitrator — src/procurement/llm_arbitrator.py

T1  : is_available() retourne False si MISTRAL_API_KEY absente (offline guard)
T2  : is_available() retourne True si MISTRAL_API_KEY presente
T3  : disambiguate_document_type retourne not_resolved si API indisponible
T4  : disambiguate_document_type parse correctement la reponse LLM
T5  : guard taxonomie — LLM hors candidats -> not_resolved
T6  : plafond confiance type_disambiguation (cap 0.85)
T7  : detect_mandatory_part retourne not_resolved si API indisponible
T8  : detect_mandatory_part parse correctement la reponse LLM
T9  : plafond confiance mandatory_part (cap 0.70)
T10 : semantic_link_documents retourne not_resolved si API indisponible
T11 : semantic_link_documents parse correctement la reponse LLM
T12 : plafond confiance semantic_link (cap 0.80)
T13 : integration MandatoryPartsEngine Level 3 — appele quand L1+L2 echouent
T14 : integration MandatoryPartsEngine Level 3 — non appele si L1 detecte
T15 : integration process_linker Level 5 SEMANTIC_LLM
T16 : reset_arbitrator efface le singleton
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────


def _make_arbitrator(api_key: str = "sk-test"):
    """Cree un LLMArbitrator avec MISTRAL_API_KEY definie."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    with patch.dict("os.environ", {"MISTRAL_API_KEY": api_key}):
        arb = LLMArbitrator()
    return arb


def _mock_llm_response(content_dict: dict) -> MagicMock:
    """Cree un mock de client Mistral retournant content_dict en JSON."""
    mock_choice = SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(content_dict))
    )
    mock_response = SimpleNamespace(choices=[mock_choice])
    mock_client = MagicMock()
    mock_client.chat.complete.return_value = mock_response
    return mock_client


# ── T1 : is_available sans API key ────────────────────────────────────────


def test_is_available_false_without_api_key(monkeypatch):
    """is_available() retourne False si MISTRAL_API_KEY absente."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    arb = LLMArbitrator()
    assert arb.is_available() is False


# ── T2 : is_available avec API key ────────────────────────────────────────


def test_is_available_true_with_api_key(monkeypatch):
    """is_available() retourne True si MISTRAL_API_KEY presente."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-valid-key")
    arb = LLMArbitrator()
    assert arb.is_available() is True


# ── T3 : disambiguate offline ─────────────────────────────────────────────


def test_disambiguate_type_offline(monkeypatch):
    """disambiguate_document_type retourne not_resolved si API indisponible."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    arb = LLMArbitrator()
    result = arb.disambiguate_document_type(
        text="Document de marche",
        candidates=["DAO", "TDR"],
        deterministic_confidence=0.50,
    )
    assert result.value is None
    assert result.confidence == 0.0
    assert any("not_resolved" in e for e in result.evidence)


# ── T4 : disambiguate parse reponse LLM ───────────────────────────────────


def test_disambiguate_type_parses_llm_response(monkeypatch):
    """disambiguate_document_type retourne le type parse depuis la reponse LLM."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")

    mock_client = _mock_llm_response(
        {"type": "DAO", "confidence": 0.80, "evidence": "Mention DAO en page 1"}
    )

    arb = LLMArbitrator()
    with patch.object(arb, "_get_client", return_value=mock_client):
        result = arb.disambiguate_document_type(
            text="Dossier Appel d'Offres national...",
            candidates=["DAO", "TDR", "UNKNOWN"],
            deterministic_confidence=0.55,
        )

    assert result.value == "DAO"
    assert result.confidence <= 0.85
    assert any("llm_arbitration" in e for e in result.evidence)


# ── T5 : guard taxonomie ──────────────────────────────────────────────────


def test_disambiguate_type_rejects_out_of_taxonomy(monkeypatch):
    """LLM ne peut pas retourner un type hors des candidats proposes."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")

    mock_client = _mock_llm_response(
        {"type": "CONTRAT_CADRE_INVENTÉ", "confidence": 0.99, "evidence": "..."}
    )

    arb = LLMArbitrator()
    with patch.object(arb, "_get_client", return_value=mock_client):
        result = arb.disambiguate_document_type(
            text="...",
            candidates=["DAO", "TDR"],
            deterministic_confidence=0.40,
        )

    assert result.value is None
    assert result.confidence == 0.0
    assert any("out_of_taxonomy" in e or "not_resolved" in e for e in result.evidence)


# ── T6 : plafond confiance type ───────────────────────────────────────────


def test_disambiguate_type_confidence_capped(monkeypatch):
    """Confiance retournee par LLM est plafonnee a 0.85 meme si LLM dit 0.99."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")

    mock_client = _mock_llm_response(
        {"type": "DAO", "confidence": 0.99, "evidence": "Tres confiant"}
    )

    arb = LLMArbitrator()
    with patch.object(arb, "_get_client", return_value=mock_client):
        result = arb.disambiguate_document_type(
            text="Appel d'offres...",
            candidates=["DAO", "TDR"],
            deterministic_confidence=0.60,
        )

    assert result.confidence <= 0.85


# ── T7 : detect_mandatory_part offline ────────────────────────────────────


def test_detect_mandatory_part_offline(monkeypatch):
    """detect_mandatory_part retourne not_resolved si API indisponible."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    arb = LLMArbitrator()
    result = arb.detect_mandatory_part(
        text_excerpt="...",
        part_name="budget_detaille",
        part_description="Budget ligne a ligne",
    )
    assert result.value is None
    assert result.confidence == 0.0


# ── T8 : detect_mandatory_part parse reponse ─────────────────────────────


def test_detect_mandatory_part_parses_response(monkeypatch):
    """detect_mandatory_part parse correctement detected + evidence."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")

    mock_client = _mock_llm_response(
        {
            "detected": True,
            "confidence": 0.65,
            "evidence": "Section 'Budget previsionnel' presente en page 3",
        }
    )

    arb = LLMArbitrator()
    with patch.object(arb, "_get_client", return_value=mock_client):
        result = arb.detect_mandatory_part(
            text_excerpt="... Budget previsionnel: 50 000 USD ...",
            part_name="budget_detaille",
            part_description="Budget ligne par ligne",
        )

    assert result.value is True
    assert result.confidence <= 0.70
    assert any("llm_arbitration" in e for e in result.evidence)


# ── T9 : plafond confiance mandatory_part ────────────────────────────────


def test_detect_mandatory_part_confidence_capped(monkeypatch):
    """Confiance plafonnee a 0.70 pour Level 3 mandatory parts."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")

    mock_client = _mock_llm_response(
        {"detected": True, "confidence": 0.95, "evidence": "Certains"}
    )

    arb = LLMArbitrator()
    with patch.object(arb, "_get_client", return_value=mock_client):
        result = arb.detect_mandatory_part(
            text_excerpt="...", part_name="scope_travaux"
        )

    assert result.confidence <= 0.70


# ── T10 : semantic_link offline ───────────────────────────────────────────


def test_semantic_link_offline(monkeypatch):
    """semantic_link_documents retourne not_resolved si API indisponible."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    arb = LLMArbitrator()
    result = arb.semantic_link_documents(
        doc_a_summary="Type: DAO, Ref: DAO-2025-001",
        doc_b_summary="Type: OFFRE_FINANCIERE, Ref: None",
    )
    assert result.value is None
    assert result.confidence == 0.0


# ── T11 : semantic_link parse reponse ─────────────────────────────────────


def test_semantic_link_parses_response(monkeypatch):
    """semantic_link_documents parse linked + link_nature."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")

    mock_client = _mock_llm_response(
        {
            "linked": True,
            "link_nature": "offer_to_dao",
            "confidence": 0.75,
            "evidence": "Meme projet Bamako 2025, meme entite SCI",
        }
    )

    arb = LLMArbitrator()
    with patch.object(arb, "_get_client", return_value=mock_client):
        result = arb.semantic_link_documents(
            doc_a_summary="Type: OFFRE_FINANCIERE, Projet: Bamako 2025",
            doc_b_summary="Type: DAO, Ref: DAO-BKO-2025, Entite: SCI",
        )

    assert result.value is True
    assert result.confidence <= 0.80
    assert any("link_nature" in e for e in result.evidence)


# ── T12 : plafond confiance semantic_link ─────────────────────────────────


def test_semantic_link_confidence_capped(monkeypatch):
    """Confiance plafonnee a 0.80 pour semantic link."""
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    reset_arbitrator()
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")

    mock_client = _mock_llm_response(
        {
            "linked": True,
            "link_nature": "offer_to_dao",
            "confidence": 1.0,
            "evidence": "Sur",
        }
    )

    arb = LLMArbitrator()
    with patch.object(arb, "_get_client", return_value=mock_client):
        result = arb.semantic_link_documents("Doc A", "Doc B")

    assert result.confidence <= 0.80


# ── T13 : integration MandatoryPartsEngine Level 3 ────────────────────────


def test_mandatory_parts_engine_calls_level3_when_l1_l2_fail(tmp_path, monkeypatch):
    """MandatoryPartsEngine Level 3 appele quand L1+L2 echouent."""
    from src.procurement.llm_arbitrator import LLMArbitrator
    from src.procurement.mandatory_parts_engine import MandatoryPartsEngine

    # Mock arbitrator
    mock_arb = MagicMock(spec=LLMArbitrator)
    from src.procurement.procedure_models import TracedField

    mock_arb.detect_mandatory_part.return_value = TracedField(
        value=True,
        confidence=0.65,
        evidence=["llm_arbitration:mistral-large-latest", "part:budget_previsionnel"],
    )

    engine = MandatoryPartsEngine(llm_arbitrator=mock_arb)
    known_types = engine.known_types

    if not known_types:
        pytest.skip("Aucun type charge depuis config/mandatory_parts/")

    doc_kind = next(iter(known_types))
    rules = engine.get_rules(doc_kind)
    if not rules or not rules.mandatory:
        pytest.skip(f"Aucune regle mandatory pour {doc_kind}")

    # Texte delibrement vide pour forcer L1+L2 a echouer sur toutes les regles
    text = "texte sans aucune section ni mot-cle reconnu"
    results, _, _ = engine.detect_parts(text, doc_kind)

    # Level 3 doit avoir ete appele au moins une fois (une fois par regle ou L1+L2 echouent)
    assert mock_arb.detect_mandatory_part.call_count >= 1


# ── T14 : Level 3 non appele si L1 detecte ────────────────────────────────


def test_mandatory_parts_level3_not_called_if_l1_detected(monkeypatch):
    """Level 3 LLM non appele si L1 heading detect reussit."""
    from unittest.mock import MagicMock

    from src.procurement.llm_arbitrator import LLMArbitrator
    from src.procurement.mandatory_parts_engine import MandatoryPartsEngine

    mock_arb = MagicMock(spec=LLMArbitrator)
    engine = MandatoryPartsEngine(llm_arbitrator=mock_arb)
    known_types = engine.known_types

    if not known_types:
        pytest.skip("Aucun type charge")

    doc_kind = next(iter(known_types))
    rules = engine.get_rules(doc_kind)
    if not rules or not rules.mandatory:
        pytest.skip(f"Aucune regle mandatory pour {doc_kind}")

    # Construire un texte qui match le Level 1 du premier pattern
    first_rule = rules.mandatory[0]
    if not first_rule.level_1_patterns:
        pytest.skip("Pas de L1 pattern")

    # Utiliser le pattern regex directement pour construire un texte matchant
    text = f"{first_rule.part_name} : contenu de la section"

    engine.detect_parts(text, doc_kind)
    # Si L1 detecte pour la premiere regle, Level 3 ne doit jamais etre appele
    assert mock_arb.detect_mandatory_part.call_count == 0


# ── T15 : integration process_linker Level 5 ─────────────────────────────


def test_process_linker_semantic_level5(monkeypatch):
    """process_linker appelle LLM semantic link quand pair contextuelle et fuzzy insuffisant."""
    from src.procurement.document_ontology import DocumentKindParent
    from src.procurement.llm_arbitrator import LLMArbitrator
    from src.procurement.procedure_models import TracedField
    from src.procurement.process_linker import DocumentSummary, link_documents

    mock_arb = MagicMock(spec=LLMArbitrator)
    mock_arb.semantic_link_documents.return_value = TracedField(
        value=True,
        confidence=0.72,
        evidence=["llm_arbitration:mistral-large-latest", "link_nature:offer_to_dao"],
    )

    source = DocumentSummary(
        document_id="offre-001",
        document_kind=DocumentKindParent.OFFER_FINANCIAL,
        procedure_reference=None,
        issuing_entity="Cabinet XYZ",
        project_name=None,
        zones=[],
        submission_deadline=None,
    )
    target = DocumentSummary(
        document_id="dao-001",
        document_kind=DocumentKindParent.DAO,
        procedure_reference=None,
        issuing_entity="Cabinet XYZ",
        project_name=None,
        zones=[],
        submission_deadline=None,
    )

    hints = link_documents(source, [target], llm_arbitrator=mock_arb)

    # LLM doit avoir ete appele exactement une fois (paire OFFRE/DAO contextuelle)
    assert mock_arb.semantic_link_documents.call_count == 1

    # Le hint SEMANTIC_LLM doit etre present — le mock retourne value=True conf=0.72
    assert len(hints) >= 1
    levels = [h.link_level for h in hints]
    assert "SEMANTIC_LLM" in levels, f"SEMANTIC_LLM attendu, obtenus : {levels}"


# ── T16 : reset_arbitrator ────────────────────────────────────────────────


def test_reset_arbitrator_clears_singleton(monkeypatch):
    """reset_arbitrator efface le singleton — test isolation."""
    from src.procurement.llm_arbitrator import get_arbitrator, reset_arbitrator

    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    arb1 = get_arbitrator()
    arb2 = get_arbitrator()
    assert arb1 is arb2  # singleton

    reset_arbitrator()
    arb3 = get_arbitrator()
    assert arb3 is not arb1  # nouveau singleton apres reset


# ── T17 : YAML config charge — valeurs overrident constantes ──────────────


def test_yaml_config_loaded_overrides_defaults(tmp_path, monkeypatch):
    """LLMArbitrator charge llm_arbitration.yaml et overide les constantes par defaut."""
    import yaml

    from src.procurement import llm_arbitrator as arb_mod
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    yaml_content = {
        "arbitration": {
            "enabled": True,
            "model": "mistral-small-latest",
            "timeout_seconds": 5,
            "max_retries": 2,
        },
        "thresholds": {
            "type_disambiguation": {"max_llm_confidence": 0.75},
            "mandatory_parts_l3": {"max_llm_confidence": 0.60},
            "process_linking": {"max_llm_confidence": 0.70},
        },
    }
    yaml_file = tmp_path / "llm_arbitration.yaml"
    yaml_file.write_text(yaml.dump(yaml_content), encoding="utf-8")

    reset_arbitrator()
    monkeypatch.setattr(arb_mod, "_CONFIG_PATH", yaml_file)

    arb = LLMArbitrator()

    assert arb._model == "mistral-small-latest"
    assert arb._timeout == 5
    assert arb._max_retries == 2
    assert arb._max_conf_type == 0.75
    assert arb._max_conf_parts == 0.60
    assert arb._max_conf_link == 0.70


# ── T18 : YAML absent — fallback sur constantes ───────────────────────────


def test_yaml_absent_fallback_to_defaults(tmp_path, monkeypatch):
    """Si llm_arbitration.yaml absent, constantes par defaut utilisees."""
    from src.procurement import llm_arbitrator as arb_mod
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    missing_path = tmp_path / "nonexistent.yaml"
    reset_arbitrator()
    monkeypatch.setattr(arb_mod, "_CONFIG_PATH", missing_path)

    arb = LLMArbitrator()

    assert arb._model == "mistral-large-latest"
    assert arb._timeout == 10
    assert arb._max_conf_type == 0.85
    assert arb._max_conf_parts == 0.70
    assert arb._max_conf_link == 0.80


# ── T19 : enabled=false desactive is_available meme avec API key ──────────


def test_yaml_enabled_false_disables_arbitrator(tmp_path, monkeypatch):
    """Si enabled=false dans YAML, is_available() retourne False meme avec API key."""
    import yaml

    from src.procurement import llm_arbitrator as arb_mod
    from src.procurement.llm_arbitrator import LLMArbitrator, reset_arbitrator

    yaml_content = {"arbitration": {"enabled": False}}
    yaml_file = tmp_path / "llm_arbitration.yaml"
    yaml_file.write_text(yaml.dump(yaml_content), encoding="utf-8")

    reset_arbitrator()
    monkeypatch.setattr(arb_mod, "_CONFIG_PATH", yaml_file)
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")

    arb = LLMArbitrator()
    assert arb.is_available() is False


# ── T20 : _safe_json log warning si JSON invalide ─────────────────────────


def test_safe_json_logs_warning_on_invalid_json(caplog):
    """_safe_json log un WARNING si le JSON est invalide."""
    import logging

    from src.procurement.llm_arbitrator import _safe_json

    with caplog.at_level(logging.WARNING, logger="src.procurement.llm_arbitrator"):
        result = _safe_json("ceci n'est pas du JSON valide {{{")

    assert result == {}
    assert any(
        "_safe_json" in r.message and "echec parse JSON" in r.message
        for r in caplog.records
    )


# ── T21 : pass_1b injecte arbitrateur dans MandatoryPartsEngine ───────────


def test_pass_1b_injects_arbitrator_when_available(monkeypatch):
    """pass_1b instancie MandatoryPartsEngine avec llm_arbitrator quand API disponible."""
    from unittest.mock import MagicMock

    import src.annotation.passes.pass_1b_document_validity as p1b_mod
    from src.procurement.llm_arbitrator import reset_arbitrator

    reset_arbitrator()
    p1b_mod._mp_engine = None  # force reinit

    mock_arb = MagicMock()
    mock_arb.is_available.return_value = True

    with patch(
        "src.annotation.passes.pass_1b_document_validity.get_arbitrator",
        return_value=mock_arb,
    ):
        engine = p1b_mod._get_engine()

    assert engine._llm_arbitrator is mock_arb
    p1b_mod._mp_engine = None  # nettoyage


# ── T22 : pass_1d passe arbitrateur a build_process_linking ───────────────


def test_pass_1d_passes_arbitrator_to_process_linking(monkeypatch):
    """pass_1d passe l'arbitrateur a build_process_linking quand API disponible."""
    import uuid
    from unittest.mock import MagicMock, patch

    from src.procurement.llm_arbitrator import reset_arbitrator

    reset_arbitrator()

    mock_arb = MagicMock()
    mock_arb.is_available.return_value = True

    captured_kwargs: dict = {}

    def _mock_build(source, candidates, text, llm_arbitrator=None):
        captured_kwargs["llm_arbitrator"] = llm_arbitrator
        from src.procurement.document_ontology import ProcessRole
        from src.procurement.procedure_models import ProcessLinking, TracedField

        return ProcessLinking(
            process_role=TracedField(
                value=ProcessRole.UNKNOWN, confidence=0.5, evidence=[]
            ),
            procedure_end_marker=TracedField(value="no", confidence=0.5, evidence=[]),
        )

    with patch(
        "src.annotation.passes.pass_1d_process_linking.get_arbitrator",
        return_value=mock_arb,
    ):
        with patch(
            "src.annotation.passes.pass_1d_process_linking.build_process_linking",
            side_effect=_mock_build,
        ):
            from src.annotation.passes.pass_1d_process_linking import (
                run_pass_1d_process_linking,
            )

            run_pass_1d_process_linking(
                normalized_text="texte test",
                document_id="doc-001",
                run_id=uuid.uuid4(),
                pass_1a_output_data={},
            )

    assert captured_kwargs.get("llm_arbitrator") is mock_arb
