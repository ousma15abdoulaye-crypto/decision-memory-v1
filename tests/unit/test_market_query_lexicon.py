"""Tests heuristique prix marché (bypass guardrail INV-W06)."""

from __future__ import annotations

from src.agent.market_query_lexicon import looks_like_factual_market_price_query


class TestLooksLikeFactualMarketPriceQuery:
    def test_bamako_cement(self):
        assert looks_like_factual_market_price_query(
            "Prix du ciment à Bamako ce mois ?"
        )
        assert looks_like_factual_market_price_query("quel est le prix du riz à Mopti")

    def test_tarif_combien(self):
        assert looks_like_factual_market_price_query("Tarif gasoil Bamako")
        assert looks_like_factual_market_price_query("Combien coûte le ciment")

    def test_not_price_only_location(self):
        assert not looks_like_factual_market_price_query("Quelle est la météo à Bamako")

    def test_blocks_recommendation_phrases(self):
        assert not looks_like_factual_market_price_query(
            "Quel fournisseur est le meilleur pour le ciment ?"
        )
        assert not looks_like_factual_market_price_query("Qui est le gagnant ?")

    def test_recommendation_even_with_prix_word(self):
        assert not looks_like_factual_market_price_query(
            "À quel prix devrions-nous attribuer le marché au meilleur fournisseur ?"
        )
