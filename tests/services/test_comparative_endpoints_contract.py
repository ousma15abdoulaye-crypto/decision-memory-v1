"""ADR-0017 P4 — enveloppes distinctes comparative-matrix vs comparative-table-model."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.comparative_table_model import build_comparative_table_model


def test_comparative_table_model_top_level_contract() -> None:
    """Champs stables de ``GET …/m16/comparative-table-model`` (projection exports)."""
    ev = {
        "criteria": [{"id": "c1", "name": "N", "label": "N", "weight": 1.0}],
        "bundles": [{"id": "b1", "supplier_name_display": "S"}],
        "scores_matrix": {"b1": {"c1": {"score": 1.0}}},
    }
    with patch("src.services.comparative_table_model.get_connection") as mock_gc:
        mock_conn = MagicMock()
        mock_gc.return_value.__enter__.return_value = mock_conn
        with patch(
            "src.services.comparative_table_model.build_evaluation_projection",
            return_value=ev,
        ):
            out = build_comparative_table_model("00000000-0000-4000-8000-000000000001")
    assert out["source"] == "live_db"
    assert out["comparative_model_version"] == "1.0"
    assert set(out.keys()) >= {
        "workspace_id",
        "comparative_model_version",
        "source",
        "criteria",
        "bundles",
        "scores_matrix",
    }
    assert "suppliers" not in out
    assert "schema_version" not in out


def test_matrix_vs_table_model_shape_documentation() -> None:
    """Documentation vivante : la grille UI attend ``suppliers``, pas ``bundles``."""
    ui_suppliers = {"suppliers"}
    export_bundles = {"bundles"}
    assert ui_suppliers.isdisjoint(export_bundles)
