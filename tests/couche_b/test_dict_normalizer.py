"""Tests normalizer · zéro DB · RÈGLE-21."""

from __future__ import annotations

import pytest

from src.couche_b.dictionary.normalizer import (
    generate_deterministic_id,
    normalize_label,
)


class TestNormalizeLabel:

    def test_gasoil_inchange(self):
        assert normalize_label("gasoil") == "gasoil"

    def test_ciment_cpa_42_5(self):
        r = normalize_label("ciment CPA 42.5")
        assert "ciment" in r
        assert "cpa" in r
        assert "42.5" in r or "42" in r

    def test_fer_ha_majuscules(self):
        assert normalize_label("FER HA 10mm") == "fer_ha_10mm"

    def test_accent_supprime(self):
        assert normalize_label("Ségou") == normalize_label("Segou")
        assert normalize_label("gasoïl") == "gasoil"

    def test_idempotent(self):
        raw = "Ciment Portland 50kg"
        assert normalize_label(raw) == normalize_label(
            normalize_label(raw)
        )

    def test_vide(self):
        assert normalize_label("") == ""

    def test_espaces_seuls(self):
        assert normalize_label("   ") == ""

    def test_stopwords(self):
        r = normalize_label("de la peinture de qualite")
        tokens = r.split("_")
        assert "de" not in tokens
        assert "peinture" in tokens

    def test_bag_alias_sac(self):
        r = normalize_label("bag ciment 50kg")
        assert "sac" in r
        assert "ciment" in r


class TestDeterministicId:

    def test_idempotent(self):
        assert (generate_deterministic_id("gasoil") ==
                generate_deterministic_id("gasoil"))

    def test_prefix(self):
        assert generate_deterministic_id("x", "di").startswith("di-")
        assert generate_deterministic_id("x", "da").startswith("da-")

    def test_differents(self):
        assert (generate_deterministic_id("gasoil") !=
                generate_deterministic_id("ciment"))

    def test_longueur(self):
        # prefix(2) + tiret(1) + hash(16) = 19
        assert len(generate_deterministic_id("test", "di")) == 19


class TestMatchResult:

    def test_frozen(self):
        from src.couche_b.dictionary.matcher import MatchMethod, MatchResult
        r = MatchResult(
            item_id="gasoil", canonical_form="Gasoil",
            unit_canonical="litre", family_id="carburants",
            confidence=0.95, match_method=MatchMethod.EXACT,
            requires_review=False, evidence="gasoil",
        )
        with pytest.raises(AttributeError):
            r.confidence = 0.5  # type: ignore

    def test_to_dict(self):
        from src.couche_b.dictionary.matcher import MatchMethod, MatchResult
        r = MatchResult(
            item_id="gasoil", canonical_form="Gasoil",
            unit_canonical="litre", family_id="carburants",
            confidence=0.95, match_method=MatchMethod.EXACT,
            requires_review=False, evidence="gasoil",
        )
        d = r.to_dict()
        assert d["match_method"] == "exact"
        assert d["requires_review"] is False
