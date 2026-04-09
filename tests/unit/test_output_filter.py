"""Tests Output Filter INV-W06 — Canon V5.1.0.

Vérifie que le filtre post-LLM détecte et remplace les patterns interdits
dans le flux de tokens streamés, sans altérer les tokens legítimes.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from src.agent.output_filter import _apply_patterns, filter_token_stream


def _run(coro):
    return asyncio.run(coro)


def _make_trace():
    trace = MagicMock()
    trace.update = MagicMock()
    return trace


async def _collect_events(events: list[dict]) -> list[dict]:
    """Collecte les événements filtrés depuis une liste de dicts."""

    async def _gen():
        for e in events:
            yield e

    trace = _make_trace()
    result = []
    async for ev in filter_token_stream(_gen(), trace):
        result.append(ev)
    return result


class TestApplyPatterns:
    def test_winner_replaced(self):
        filtered, triggered = _apply_patterns("Le winner est ce fournisseur.")
        assert "[CONTENU FILTRÉ — INV-W06]" in filtered
        assert triggered is True

    def test_gagnant_replaced(self):
        filtered, triggered = _apply_patterns("Le gagnant du marché est X.")
        assert "[CONTENU FILTRÉ — INV-W06]" in filtered
        assert triggered is True

    def test_recommandation_replaced(self):
        filtered, triggered = _apply_patterns("Ma recommandation est claire.")
        assert "[CONTENU FILTRÉ — INV-W06]" in filtered
        assert triggered is True

    def test_classement_replaced(self):
        filtered, triggered = _apply_patterns("Voici le classement des offres.")
        assert "[CONTENU FILTRÉ — INV-W06]" in filtered
        assert triggered is True

    def test_meilleur_fournisseur_replaced(self):
        filtered, triggered = _apply_patterns("Le meilleur fournisseur est Alpha SARL.")
        assert "[CONTENU FILTRÉ — INV-W06]" in filtered
        assert triggered is True

    def test_clean_text_untouched(self):
        text = "Le prix médian du ciment à Bamako est 7 500 FCFA."
        filtered, triggered = _apply_patterns(text)
        assert filtered == text
        assert triggered is False

    def test_factual_data_untouched(self):
        text = "Données : 5 offres reçues, 3 campagnes actives."
        filtered, triggered = _apply_patterns(text)
        assert filtered == text
        assert triggered is False


class TestFilterTokenStream:
    def test_passes_through_clean_tokens(self):
        events = [
            {"type": "token", "content": "Le prix du ciment est "},
            {"type": "token", "content": "7 500 FCFA."},
            {"type": "done", "usage": {}},
        ]
        result = _run(_collect_events(events))
        token_events = [e for e in result if e.get("type") == "token"]
        combined = "".join(e["content"] for e in token_events)
        assert "7 500 FCFA" in combined

    def test_filters_winner_in_stream(self):
        events = [
            {"type": "token", "content": "Le "},
            {"type": "token", "content": "winner "},
            {"type": "token", "content": "est X."},
            {"type": "done", "usage": {}},
        ]
        result = _run(_collect_events(events))
        token_events = [e for e in result if e.get("type") == "token"]
        combined = "".join(e["content"] for e in token_events)
        assert "[CONTENU FILTRÉ — INV-W06]" in combined
        assert "winner" not in combined.lower()

    def test_non_token_events_pass_through(self):
        events = [
            {"type": "sources", "sources": [], "has_official_source": False},
            {"type": "token", "content": "Données."},
            {"type": "done", "usage": {}},
        ]
        result = _run(_collect_events(events))
        types = [e["type"] for e in result]
        assert "sources" in types
        assert "done" in types

    def test_trace_updated_on_filter(self):
        async def _run_with_trace():
            events = [
                {"type": "token", "content": "Le gagnant est Alpha SARL."},
                {"type": "done", "usage": {}},
            ]

            async def _gen():
                for e in events:
                    yield e

            trace = _make_trace()
            result = []
            async for ev in filter_token_stream(_gen(), trace):
                result.append(ev)
            return trace

        trace = asyncio.run(_run_with_trace())
        trace.update.assert_called()

    def test_trace_not_updated_when_no_filter(self):
        async def _run_with_trace():
            events = [
                {"type": "token", "content": "Données de marché factuelles."},
                {"type": "done", "usage": {}},
            ]

            async def _gen():
                for e in events:
                    yield e

            trace = _make_trace()
            result = []
            async for ev in filter_token_stream(_gen(), trace):
                result.append(ev)
            return trace

        trace = asyncio.run(_run_with_trace())
        trace.update.assert_not_called()

    def test_empty_stream(self):
        result = _run(_collect_events([]))
        assert result == []

    def test_pattern_split_across_buffer_boundary(self):
        """Pattern 'meilleur fournisseur' coupé à la frontière flush/overlap.

        Ingénierie : buffer = 125 chars, _FLUSH_CHARS = 120, _OVERLAP_CHARS = 60.
        - prefix    = 'a' * 54 + ' '  (55 chars, espace final = \\b avant le pattern)
        - pattern   = 'meilleur fournisseur' (20 chars) → chars 55-74
        - suffix    = ' ' + 'b' * 49  (50 chars, espace initial = \\b après le pattern)
        - frontière flush_part/overlap = position 65 (= 125 - 60)

        Le pattern débute AVANT la frontière (pos 55) et se termine APRÈS (pos 74).
        Le scan du buffer COMPLET doit le capter.
        Un scan de flush_part seul (chars 0-64) ne verrait que '...meilleur fo' — partiel,
        la regex exige le token complet 'fournisseur' pour matcher — pattern manqué.

        Note : le préfixe se termine par un espace pour créer le \\b nécessaire à la
        regex (\\bmeilleur). Un préfixe purement alphanumérique ('aaa...') adjaçant
        à 'meilleur' sans espace empêche le match — comportement voulu pour éviter les
        faux positifs, mais non représentatif de la prose LLM réelle.
        """
        from src.agent.output_filter import _FLUSH_CHARS, _OVERLAP_CHARS

        prefix = (
            "a" * 54 + " "
        )  # 55 chars — espace final = frontière \\b pour le pattern
        pattern_text = "meilleur fournisseur"
        suffix = (
            " " + "b" * 49
        )  # 50 chars — espace initial = frontière \\b après pattern
        full = prefix + pattern_text + suffix

        assert len(full) == 125, f"Buffer attendu 125, obtenu {len(full)}"
        assert len(full) > _FLUSH_CHARS, "Le buffer doit dépasser le seuil de flush"

        boundary = len(full) - _OVERLAP_CHARS  # 65
        pattern_start = 55
        pattern_end = 55 + len(pattern_text)  # 75
        assert pattern_start < boundary < pattern_end, (
            f"La frontière ({boundary}) doit couper le pattern "
            f"[{pattern_start}:{pattern_end}] pour valider le cas straddling"
        )

        events = [
            {"type": "token", "content": full},
            {"type": "done", "usage": {}},
        ]
        result = _run(_collect_events(events))
        token_events = [e for e in result if e.get("type") == "token"]
        combined = "".join(e["content"] for e in token_events)

        assert (
            "[CONTENU FILTRÉ — INV-W06]" in combined
        ), "Le pattern 'meilleur fournisseur' à la frontière buffer doit être filtré"
        assert (
            "meilleur fournisseur" not in combined.lower()
        ), "Le pattern original ne doit plus apparaître dans la sortie filtrée"
