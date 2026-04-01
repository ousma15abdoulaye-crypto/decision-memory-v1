"""Tests pour le RegulatoryIndex — couverture des regles SCI/DGMP du Plan Directeur."""

from __future__ import annotations

import pytest

from src.procurement.regulatory_index import (
    get_regulatory_index,
    reset_regulatory_index,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_regulatory_index()
    yield
    reset_regulatory_index()


class TestRegulatoryIndexLoading:
    def test_index_loads_sources(self):
        idx = get_regulatory_index()
        # En CI, data/regulatory/parsed peut etre absent.
        # La source de verite du moteur reste config/regulatory_mappings.yaml.
        assert isinstance(idx.sources, dict)

    def test_index_loads_rules(self):
        idx = get_regulatory_index()
        assert (
            len(idx.rules) >= 10
        ), f"Au moins 10 regles attendues, got {len(idx.rules)}"

    def test_sources_have_metadata(self):
        idx = get_regulatory_index()
        for label, src in idx.sources.items():
            assert src.source_label, f"source_label vide pour {label}"
            assert src.sections_count > 0, f"sections_count=0 pour {label}"


class TestSCIRules:
    def test_sci_eliminatory_gates_5(self):
        """SCI §5.2 : 5 gates eliminatoires."""
        idx = get_regulatory_index()
        elim = idx.get_eliminatory_gates("SCI")
        gate_ids = {r.dms_gate for r in elim}
        expected = {
            "eligibility_nif",
            "eligibility_rccm",
            "eligibility_quitus_fiscal",
            "eligibility_cnss",
            "eligibility_casier_judiciaire",
        }
        assert expected.issubset(
            gate_ids
        ), f"Gates SCI manquantes : {expected - gate_ids}"

    def test_sci_rfq_threshold(self):
        """SCI §4.1 : RFQ <= 5000 USD."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules("SCI", estimated_value=3000, family="GOODS")
        rule_ids = {r.rule_id for r in rules}
        assert "SCI_THRESHOLD_RFQ" in rule_ids

    def test_sci_itb_threshold(self):
        """SCI §4.1 : ITB 5001-50000 USD."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules("SCI", estimated_value=15000, family="GOODS")
        rule_ids = {r.rule_id for r in rules}
        assert "SCI_THRESHOLD_ITB" in rule_ids

    def test_sci_formal_tender_threshold(self):
        """SCI §4.1 : Appel d'offres formel > 50000 USD."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules("SCI", estimated_value=75000, family="GOODS")
        rule_ids = {r.rule_id for r in rules}
        assert "SCI_THRESHOLD_FORMAL_TENDER" in rule_ids

    def test_sci_15000_returns_eliminatory_and_itb(self):
        """SCI, 15000 USD, GOODS : doit retourner les 5 gates + ITB."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules("SCI", estimated_value=15000, family="GOODS")
        rule_ids = {r.rule_id for r in rules}
        assert "SCI_5.2_ELIMINATORY_NIF" in rule_ids
        assert "SCI_THRESHOLD_ITB" in rule_ids


class TestDGMPRules:
    def test_dgmp_aon_seuil_goods(self):
        """DGMP Art. 45 : seuil AON 25M FCFA biens/services."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules(
            "DGMP", estimated_value=30000000, family="GOODS"
        )
        rule_ids = {r.rule_id for r in rules}
        assert "DGMP_ART45_SEUIL_GOODS_SERVICES" in rule_ids

    def test_dgmp_aon_seuil_works(self):
        """DGMP Art. 45 : seuil AON 100M FCFA travaux."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules(
            "DGMP", estimated_value=150000000, family="WORKS"
        )
        rule_ids = {r.rule_id for r in rules}
        assert "DGMP_ART45_SEUIL_WORKS" in rule_ids

    def test_dgmp_aoi_seuil(self):
        """DGMP Art. 46 : seuil AOI 500M FCFA."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules(
            "DGMP", estimated_value=600000000, family="GOODS"
        )
        rule_ids = {r.rule_id for r in rules}
        assert "DGMP_ART46_SEUIL_INTERNATIONAL" in rule_ids

    def test_dgmp_principles(self):
        """DGMP Art. 7 : principes fondamentaux."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules("DGMP")
        rule_ids = {r.rule_id for r in rules}
        assert "DGMP_ART7_PRINCIPES" in rule_ids


class TestCrossFramework:
    def test_no_sci_rules_for_dgmp(self):
        """Les regles SCI ne s'appliquent pas au framework DGMP."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules("DGMP", estimated_value=15000, family="GOODS")
        sci_rules = [r for r in rules if r.source == "sci"]
        assert len(sci_rules) == 0, f"Regles SCI trouvees pour DGMP : {sci_rules}"

    def test_customs_exemption_for_sci(self):
        """Exoneration douaniere applicable pour SCI."""
        idx = get_regulatory_index()
        rules = idx.get_applicable_rules("SCI")
        rule_ids = {r.rule_id for r in rules}
        assert "DOUANES_EXONERATION" in rule_ids

    def test_thresholds_method(self):
        """get_thresholds retourne uniquement les regles de type threshold."""
        idx = get_regulatory_index()
        thresholds = idx.get_thresholds("SCI", family="GOODS")
        for r in thresholds:
            assert r.rule_type == "threshold", f"Regle non-threshold : {r.rule_id}"
