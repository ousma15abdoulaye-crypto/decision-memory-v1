"""INV-W06 — Zéro mot interdit en sortie (Canon V5.1.0 Locking test 1).

winner / rank / recommendation / selected_vendor / best_offer interdits partout.
RÈGLE-09 V4.1.0 — aucune recommandation de fournisseur.

Ce test E2E vérifie :
1. Que les schémas Pydantic (JSON serialisé) ne contiennent pas les mots interdits.
2. Que le module `pv_builder.py` (snapshot) ne contient pas les mots interdits.
3. Que `validate_pv_snapshot` rejette les snapshots contenant des champs interdits.
"""

from __future__ import annotations

import json

import pytest

_FORBIDDEN_KEYS = frozenset(
    {"winner", "rank", "recommendation", "selected_vendor", "best_offer"}
)


# ── Test 1 : Schémas Pydantic ─────────────────────────────────────


class TestInvW06Schemas:
    def test_criterion_assessment_out_no_forbidden_keys(self):
        from src.schemas.m16 import CriterionAssessmentOut

        obj = CriterionAssessmentOut(
            id="ca-1",
            workspace_id="ws-1",
            bundle_id="b-1",
            criterion_key="k1",
            cell_json={},
            assessment_status="draft",
            signal="green",
        )
        raw = json.loads(obj.model_dump_json())
        _assert_no_forbidden(raw)

    def test_m16_frame_out_no_forbidden_keys(self):
        from src.schemas.m16 import (
            CriterionAssessmentOut,
            M16EvaluationFrameOut,
            TargetType,
        )

        frame = M16EvaluationFrameOut(
            workspace_id="ws-1",
            target_type=TargetType.workspace,
            target_id="ws-1",
            domains=[],
            assessments=[
                CriterionAssessmentOut(
                    id="ca-1",
                    workspace_id="ws-1",
                    bundle_id="b-1",
                    criterion_key="k1",
                    cell_json={},
                    assessment_status="draft",
                    signal="green",
                )
            ],
            price_lines=[],
            price_values=[],
            bundle_weighted_totals={"b-1": 100.0},
            weight_validation={"valid": True, "weighted_sum": 100.0, "errors": []},
        )
        raw = json.loads(frame.model_dump_json())
        _assert_no_forbidden(raw)


# ── Test 2 : pv_builder.py source code ───────────────────────────


class TestInvW06PvBuilderSource:
    def test_kill_list_covers_all_forbidden_keys(self):
        """pv_builder._KILL_LIST contient tous les mots interdits (Canon INV-W06)."""
        from src.services.pv_builder import _KILL_LIST

        for keyword in _FORBIDDEN_KEYS:
            assert (
                keyword in _KILL_LIST
            ), f"INV-W06 — '{keyword}' absent de _KILL_LIST dans pv_builder.py"

    def test_sanitize_removes_forbidden_keys_from_scores(self):
        """_sanitize_scores_matrix retire les clés interdites des scores."""
        from src.services.pv_builder import _sanitize_scores_matrix

        dirty = {
            "supplier_a": {
                "winner": True,
                "rank": 1,
                "recommendation": "choisir",
                "score_total": 750,
            }
        }
        clean = _sanitize_scores_matrix(dirty)
        for k in _FORBIDDEN_KEYS:
            assert k not in clean.get(
                "supplier_a", {}
            ), f"INV-W06 — '{k}' pas retiré par _sanitize_scores_matrix"
        assert "score_total" in clean.get(
            "supplier_a", {}
        ), "score_total doit être conservé"

    def test_forbidden_keys_in_tree_detects_nested(self):
        """_forbidden_keys_in_tree détecte les clés interdites imbriquées."""
        from src.services.pv_builder import _forbidden_keys_in_tree

        tree = {"evaluation": {"scores_matrix": {"supplier_a": {"rank": 1}}}}
        found = _forbidden_keys_in_tree(tree)
        assert any("rank" in f for f in found), "rank non détecté dans arbre imbriqué"


# ── Test 3 : validate_pv_snapshot rejette les champs interdits ───


class TestInvW06SnapshotValidation:
    def test_validate_rejects_winner_in_nested_dict(self):
        """INV-W06 : forbidden key 'winner' rejeté dans tout le snapshot."""
        from src.services.pv_builder import validate_pv_snapshot

        bad_snapshot = {
            "process": {"workspace_id": "ws-1"},
            "evaluation": {"winner": "Fournisseur A"},
        }
        with pytest.raises(ValueError, match="winner|INV-W06"):
            validate_pv_snapshot(bad_snapshot)

    def test_validate_rejects_recommendation_key(self):
        """INV-W06 : forbidden key 'recommendation' rejeté."""
        from src.services.pv_builder import validate_pv_snapshot

        bad_snapshot = {
            "recommendation": "Choisir le fournisseur B",
            "evaluation": {"scores_matrix": {}},
        }
        with pytest.raises(ValueError, match="recommendation|INV-W06"):
            validate_pv_snapshot(bad_snapshot)

    def test_validate_rejects_rank_key(self):
        """INV-W06 : forbidden key 'rank' rejeté dans scores_matrix."""
        from src.services.pv_builder import validate_pv_snapshot

        bad_snapshot = {
            "evaluation": {
                "scores_matrix": {"fournisseur_a": {"rank": 1, "total": 750}}
            }
        }
        with pytest.raises(ValueError, match="rank|INV-W06"):
            validate_pv_snapshot(bad_snapshot)


# ── Helpers ──────────────────────────────────────────────────────


def _assert_no_forbidden(obj, path: str = "") -> None:
    """Parcourt récursivement un objet JSON et vérifie l'absence de mots interdits."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            assert (
                key.lower() not in _FORBIDDEN_KEYS
            ), f"INV-W06 — champ interdit '{key}' trouvé à {path or 'root'}"
            _assert_no_forbidden(val, path=f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_forbidden(item, path=f"{path}[{i}]")
    elif isinstance(obj, str):
        low = obj.lower()
        for kw in _FORBIDDEN_KEYS:
            assert (
                kw not in low
            ), f"INV-W06 — valeur interdite '{kw}' trouvée dans la chaîne à {path}"
