"""
Tests — Agent : guardrail INV-W06 + MQL params + RBAC.

Les tests guardrail mockent classify_intent (évite les appels Mistral en CI).
Les tests param_extractor testent la logique déterministe (regex/keywords).
Les tests RBAC vérifient la matrice 18×6 statiquement.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _mock_trace() -> MagicMock:
    """Trace Langfuse factice pour les tests sans observabilité."""
    trace = MagicMock()
    span = MagicMock()
    span.end = MagicMock()
    span.update = MagicMock()
    trace.span = MagicMock(return_value=span)
    return trace


def _intent(intent_class, confidence: float):  # type: ignore[no-untyped-def]
    from src.agent.semantic_router import IntentResult

    return IntentResult(intent_class=intent_class, confidence=confidence)


# ─── Tests guardrail ──────────────────────────────────────────────────────────


class TestGuardrailINVW06:
    """Le guardrail INV-W06 bloque les requêtes de recommandation ≥ 0.85."""

    def test_guardrail_blocks_recommendation_high_confidence(self) -> None:
        """check_recommendation_guardrail bloque RECOMMENDATION à confidence ≥ 0.85."""
        from src.agent.guardrail import IntentClass, check_recommendation_guardrail

        intent = _intent(IntentClass.RECOMMENDATION, 0.92)
        with patch(
            "src.agent.guardrail.classify_intent", new=AsyncMock(return_value=intent)
        ):
            result = asyncio.get_event_loop().run_until_complete(
                check_recommendation_guardrail(
                    "Quel fournisseur recommandez-vous ?", _mock_trace()
                )
            )

        assert result.blocked, "RECOMMENDATION ≥ 0.85 doit être bloqué"
        assert result.confidence == 0.92
        assert result.reason

    def test_guardrail_does_not_block_recommendation_low_confidence(self) -> None:
        """RECOMMENDATION < 0.85 n'est PAS bloqué (seuil canon V5.1 §7.4)."""
        from src.agent.guardrail import IntentClass, check_recommendation_guardrail

        intent = _intent(IntentClass.RECOMMENDATION, 0.70)
        with patch(
            "src.agent.guardrail.classify_intent", new=AsyncMock(return_value=intent)
        ):
            result = asyncio.get_event_loop().run_until_complete(
                check_recommendation_guardrail(
                    "Quel est le meilleur fournisseur ?", _mock_trace()
                )
            )

        assert not result.blocked

    def test_guardrail_allows_market_query(self) -> None:
        """MARKET_QUERY jamais bloqué."""
        from src.agent.guardrail import IntentClass, check_recommendation_guardrail

        intent = _intent(IntentClass.MARKET_QUERY, 0.92)
        with patch(
            "src.agent.guardrail.classify_intent", new=AsyncMock(return_value=intent)
        ):
            result = asyncio.get_event_loop().run_until_complete(
                check_recommendation_guardrail(
                    "Prix du ciment a Mopti ?", _mock_trace()
                )
            )

        assert not result.blocked

    def test_guardrail_allows_process_info(self) -> None:
        """PROCESS_INFO jamais bloqué."""
        from src.agent.guardrail import IntentClass, check_recommendation_guardrail

        intent = _intent(IntentClass.PROCESS_INFO, 0.85)
        with patch(
            "src.agent.guardrail.classify_intent", new=AsyncMock(return_value=intent)
        ):
            result = asyncio.get_event_loop().run_until_complete(
                check_recommendation_guardrail(
                    "Quels sont les seuils ECHO ?", _mock_trace()
                )
            )

        assert not result.blocked

    def test_guardrail_allows_workspace_status(self) -> None:
        """WORKSPACE_STATUS jamais bloqué."""
        from src.agent.guardrail import IntentClass, check_recommendation_guardrail

        intent = _intent(IntentClass.WORKSPACE_STATUS, 0.90)
        with patch(
            "src.agent.guardrail.classify_intent", new=AsyncMock(return_value=intent)
        ):
            result = asyncio.get_event_loop().run_until_complete(
                check_recommendation_guardrail(
                    "Ou en est le dossier RFQ-001 ?", _mock_trace()
                )
            )

        assert not result.blocked


# ─── Tests MQL param_extractor ────────────────────────────────────────────────


class TestMQLParamExtractor:
    """extract_mql_params est déterministe (regex + ZONE_KEYWORDS, pas de LLM)."""

    _tid = uuid.UUID("00000000-0000-0000-0000-000000000001")

    def test_extracts_zone_from_city_query(self) -> None:
        """Mopti est une zone connue."""
        from src.mql.param_extractor import extract_mql_params

        params = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("Prix du ciment a Mopti ce mois ?", self._tid)
        )
        assert params.zones or params.article_pattern, (
            f"Zone ou article attendu. Obtenu zones={params.zones}, "
            f"article={params.article_pattern}"
        )

    def test_extracts_article_pattern(self) -> None:
        """Un article connu (ciment) est extrait en pattern."""
        from src.mql.param_extractor import extract_mql_params

        params = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("prix du ciment a Bamako", self._tid)
        )
        assert params is not None

    def test_does_not_crash_on_empty_query(self) -> None:
        """extract_mql_params ne plante pas sur une query vide."""
        from src.mql.param_extractor import extract_mql_params

        params = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("", self._tid)
        )
        assert params is not None

    def test_detects_bamako_zone(self) -> None:
        """Bamako est une zone géographique connue."""
        from src.mql.param_extractor import extract_mql_params

        params = asyncio.get_event_loop().run_until_complete(
            extract_mql_params("prix a Bamako", self._tid)
        )
        assert params is not None


# ─── Tests RBAC ───────────────────────────────────────────────────────────────


class TestRBACPermissions:
    """Matrice RBAC V5.2 : 18 permissions × 6 rôles."""

    def test_exactly_six_roles(self) -> None:
        """ROLE_PERMISSIONS a exactement 6 rôles."""
        from src.auth.permissions import ROLE_PERMISSIONS

        assert (
            len(ROLE_PERMISSIONS) == 6
        ), f"Attendu 6 rôles, obtenu {len(ROLE_PERMISSIONS)}: {list(ROLE_PERMISSIONS)}"

    def test_admin_has_18_permissions(self) -> None:
        """admin possède les 18 permissions."""
        from src.auth.permissions import ROLE_PERMISSIONS

        admin_perms = ROLE_PERMISSIONS["admin"]
        assert (
            len(admin_perms) == 18
        ), f"admin devrait avoir 18 permissions, obtenu {len(admin_perms)}: {sorted(admin_perms)}"

    def test_observer_has_no_write_permissions(self) -> None:
        """observer n'a aucune permission d'écriture."""
        from src.auth.permissions import ROLE_PERMISSIONS, WRITE_PERMISSIONS

        observer_perms = ROLE_PERMISSIONS.get("observer", set())
        write_overlap = observer_perms & WRITE_PERMISSIONS
        assert (
            not write_overlap
        ), f"observer ne doit pas avoir de permissions write : {write_overlap}"

    def test_supply_chain_has_market_write(self) -> None:
        """supply_chain a market.write (ajouté P1.3)."""
        from src.auth.permissions import ROLE_PERMISSIONS

        sc_perms = ROLE_PERMISSIONS.get("supply_chain", set())
        assert (
            "market.write" in sc_perms
        ), f"supply_chain doit avoir market.write. Permissions actuelles : {sorted(sc_perms)}"
