"""M-V52-A — preuves synthétiques R1 (bridge M14→M16) et R3 (market_delta_pct).

Requiert PostgreSQL migré (``alembic upgrade head``) et ``DATABASE_URL``.
Pré-données minimales : ``geo_master``, ``users``, ``couche_b.procurement_dict_items``
(R3 skippé si dict ou geo absents).
"""

from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal

import psycopg
import psycopg.rows
import pytest

from src.db.core import _ConnectionWrapper
from src.services.m14_bridge import _run_bridge
from src.services.market_delta import persist_market_deltas_for_workspace
from src.services.market_signal_lookup import normalize_label_to_item_slug


def _require_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL non défini")


def _connect_admin() -> tuple[_ConnectionWrapper, psycopg.Connection]:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    raw = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
    raw.autocommit = True
    wrap = _ConnectionWrapper(raw)
    wrap.execute("SELECT set_config('app.is_admin', 'true', true)", {})
    return wrap, raw


def _cleanup_v52_synthetic(
    wrap: _ConnectionWrapper,
    *,
    ws_id: str,
    tenant_id: str,
    case_id: str | None,
    committee_id: str | None,
    eval_doc_id: str | None,
    bundle_id: str | None,
    crit_id: str | None,
    plc_id: str | None,
    plbv_id: str | None,
    msv2_delete: bool,
    item_id: str | None,
    zone_id: str | None,
) -> None:
    for tbl, col, val in [
        ("criterion_assessments", "workspace_id", ws_id),
        ("evaluation_documents", "workspace_id", ws_id),
        ("price_line_bundle_values", "workspace_id", ws_id),
        ("price_line_comparisons", "workspace_id", ws_id),
        ("supplier_bundles", "workspace_id", ws_id),
        ("dao_criteria", "workspace_id", ws_id),
        ("process_workspaces", "id", ws_id),
    ]:
        try:
            wrap.execute(
                f"DELETE FROM {tbl} WHERE {col} = CAST(:v AS uuid)", {"v": val}
            )
        except Exception:  # noqa: BLE001
            pass
    if committee_id:
        try:
            wrap.execute(
                "DELETE FROM committees WHERE committee_id = CAST(:c AS uuid)",
                {"c": committee_id},
            )
        except Exception:  # noqa: BLE001
            pass
    if case_id:
        try:
            wrap.execute("DELETE FROM cases WHERE id = :c", {"c": case_id})
        except Exception:  # noqa: BLE001
            pass
    try:
        wrap.execute(
            "DELETE FROM tenants WHERE id = CAST(:t AS uuid)", {"t": tenant_id}
        )
    except Exception:  # noqa: BLE001
        pass
    if msv2_delete and item_id and zone_id:
        try:
            wrap.execute(
                """
                DELETE FROM market_signals_v2
                WHERE item_id = :i AND zone_id = :z
                """,
                {"i": item_id, "z": zone_id},
            )
        except Exception:  # noqa: BLE001
            pass


@pytest.mark.db
class TestV52R1BridgeSynthetic:
    def test_r1_bridge_populates_criterion_assessments_from_scores_matrix(self) -> None:
        """R1 : scores_matrix M14 → cell_json avec source m14."""
        _require_database_url()
        wrap, raw = _connect_admin()

        tenant_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        committee_id = str(uuid.uuid4())
        ws_id = str(uuid.uuid4())
        bundle_id = str(uuid.uuid4())
        crit_id = str(uuid.uuid4())
        eval_doc_id = str(uuid.uuid4())

        wrap.execute(
            "INSERT INTO tenants (id, code, name) VALUES (:tid, :code, :name)",
            {
                "tid": tenant_id,
                "code": f"v52a_{tenant_id[:8]}",
                "name": "V52-A synthetic",
            },
        )
        wrap.execute("SELECT id FROM users LIMIT 1", {})
        urow = wrap.fetchone()
        assert urow is not None, "users requis"
        user_id = int(urow["id"])

        wrap.execute(
            """
            INSERT INTO cases (id, case_type, title, created_at, status, owner_id, tenant_id)
            VALUES (:cid, 'DAO', 'V52-A R1', NOW()::TEXT, 'open', :uid, :tid::text)
            """,
            {"cid": case_id, "uid": user_id, "tid": tenant_id},
        )
        wrap.execute(
            """
            INSERT INTO committees
                (committee_id, case_id, org_id, committee_type, status, created_by)
            VALUES (CAST(:com AS uuid), :cid, 'org-v52', 'achat', 'draft', 'test')
            """,
            {"com": committee_id, "cid": case_id},
        )
        wrap.execute(
            """
            INSERT INTO process_workspaces
                (id, tenant_id, created_by, reference_code, title, process_type, status)
            VALUES (CAST(:ws AS uuid), CAST(:tid AS uuid), :uid, :ref, :title,
                    'devis_simple', 'draft')
            """,
            {
                "ws": ws_id,
                "tid": tenant_id,
                "uid": user_id,
                "ref": f"V52A-{ws_id[:8]}",
                "title": "WS V52-A R1",
            },
        )
        wrap.execute(
            """
            INSERT INTO supplier_bundles
                (id, workspace_id, tenant_id, vendor_name_raw, bundle_index)
            VALUES (CAST(:bid AS uuid), CAST(:ws AS uuid), CAST(:tid AS uuid),
                    'Vendor V52', 1)
            """,
            {"bid": bundle_id, "ws": ws_id, "tid": tenant_id},
        )
        wrap.execute(
            """
            INSERT INTO dao_criteria
                (id, workspace_id, categorie, critere_nom, description,
                 ponderation, type_reponse, created_at, criterion_category, is_eliminatory)
            VALUES (:cid, CAST(:ws AS uuid), 'tech', 'Critère V52', '',
                    10.0, 'numeric', NOW(), 'essential', false)
            """,
            {"cid": crit_id, "ws": ws_id},
        )
        matrix = {
            bundle_id: {
                crit_id: {"score": 0.8, "confidence": 0.8},
            }
        }
        wrap.execute(
            """
            INSERT INTO evaluation_documents
                (id, workspace_id, committee_id, version, scores_matrix, status)
            VALUES (CAST(:eid AS uuid), CAST(:ws AS uuid), CAST(:com AS uuid),
                    1, CAST(:sm AS jsonb), 'draft')
            """,
            {
                "eid": eval_doc_id,
                "ws": ws_id,
                "com": committee_id,
                "sm": json.dumps(matrix),
            },
        )

        try:
            result = _run_bridge(wrap, ws_id)
            assert result.errors == [], result.errors
            assert result.created >= 1, result

            wrap.execute(
                """
                SELECT cell_json->>'source' AS src, cell_json->>'m14_original' AS orig
                FROM criterion_assessments
                WHERE workspace_id = CAST(:ws AS uuid) AND bundle_id = CAST(:b AS uuid)
                """,
                {"ws": ws_id, "b": bundle_id},
            )
            row = wrap.fetchone()
            assert row is not None
            assert row.get("src") == "m14"
            assert row.get("orig") == "true"
        finally:
            _cleanup_v52_synthetic(
                wrap,
                ws_id=ws_id,
                tenant_id=tenant_id,
                case_id=case_id,
                committee_id=committee_id,
                eval_doc_id=eval_doc_id,
                bundle_id=bundle_id,
                crit_id=crit_id,
                plc_id=None,
                plbv_id=None,
                msv2_delete=False,
                item_id=None,
                zone_id=None,
            )
            raw.close()


@pytest.mark.db
class TestV52R3MarketDeltaSynthetic:
    def test_r3_persist_market_delta_pct(self) -> None:
        """R3 : price_line_bundle_values.market_delta_pct aligné sur market_signals_v2."""
        _require_database_url()
        wrap, raw = _connect_admin()

        wrap.execute(
            "SELECT id FROM geo_master LIMIT 1",
            {},
        )
        zrow = wrap.fetchone()
        if not zrow:
            pytest.skip("geo_master vide — impossible de poser zone_id workspace")
        zone_id = str(zrow["id"])

        wrap.execute(
            "SELECT item_id FROM couche_b.procurement_dict_items LIMIT 1",
            {},
        )
        irow = wrap.fetchone()
        if not irow:
            pytest.skip("couche_b.procurement_dict_items vide — FK market_signals_v2")
        item_id = str(irow["item_id"])
        label_for_slug = item_id

        tenant_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        committee_id = str(uuid.uuid4())
        ws_id = str(uuid.uuid4())
        bundle_id = str(uuid.uuid4())
        plc_id = str(uuid.uuid4())
        plbv_id = str(uuid.uuid4())

        wrap.execute(
            "INSERT INTO tenants (id, code, name) VALUES (:tid, :code, :name)",
            {
                "tid": tenant_id,
                "code": f"v52r3_{tenant_id[:8]}",
                "name": "V52-R3 synthetic",
            },
        )
        wrap.execute("SELECT id FROM users LIMIT 1", {})
        urow = wrap.fetchone()
        assert urow is not None
        user_id = int(urow["id"])

        wrap.execute(
            """
            INSERT INTO cases (id, case_type, title, created_at, status, owner_id, tenant_id)
            VALUES (:cid, 'DAO', 'V52-A R3', NOW()::TEXT, 'open', :uid, :tid::text)
            """,
            {"cid": case_id, "uid": user_id, "tid": tenant_id},
        )
        wrap.execute(
            """
            INSERT INTO committees
                (committee_id, case_id, org_id, committee_type, status, created_by)
            VALUES (CAST(:com AS uuid), :cid, 'org-v52', 'achat', 'draft', 'test')
            """,
            {"com": committee_id, "cid": case_id},
        )
        wrap.execute(
            """
            INSERT INTO process_workspaces
                (id, tenant_id, created_by, reference_code, title, process_type,
                 status, zone_id)
            VALUES (CAST(:ws AS uuid), CAST(:tid AS uuid), :uid, :ref, :title,
                    'devis_simple', 'draft', :zid)
            """,
            {
                "ws": ws_id,
                "tid": tenant_id,
                "uid": user_id,
                "ref": f"V52R3-{ws_id[:8]}",
                "title": "WS V52-R3",
                "zid": zone_id,
            },
        )
        wrap.execute(
            """
            INSERT INTO supplier_bundles
                (id, workspace_id, tenant_id, vendor_name_raw, bundle_index)
            VALUES (CAST(:bid AS uuid), CAST(:ws AS uuid), CAST(:tid AS uuid),
                    'Vendor R3', 1)
            """,
            {"bid": bundle_id, "ws": ws_id, "tid": tenant_id},
        )

        market_price = Decimal("100.0000")
        wrap.execute(
            """
            INSERT INTO market_signals_v2
                (item_id, zone_id, tenant_id, price_seasonal_adj,
                 signal_quality, formula_version)
            VALUES (:iid, :zid, CAST(:tid AS uuid), :price, 'strong', '1.1')
            ON CONFLICT (item_id, zone_id) DO UPDATE SET
                price_seasonal_adj = EXCLUDED.price_seasonal_adj,
                signal_quality = EXCLUDED.signal_quality,
                tenant_id = EXCLUDED.tenant_id
            """,
            {"iid": item_id, "zid": zone_id, "tid": tenant_id, "price": market_price},
        )

        wrap.execute(
            """
            INSERT INTO price_line_comparisons
                (id, workspace_id, tenant_id, line_code, label)
            VALUES (CAST(:pid AS uuid), CAST(:ws AS uuid), CAST(:tid AS uuid),
                    'L-V52-R3', :lbl)
            """,
            {"pid": plc_id, "ws": ws_id, "tid": tenant_id, "lbl": label_for_slug},
        )
        supplier_amount = Decimal("115.000000")
        wrap.execute(
            """
            INSERT INTO price_line_bundle_values
                (id, price_line_id, bundle_id, workspace_id, tenant_id, amount)
            VALUES (CAST(:vid AS uuid), CAST(:pid AS uuid), CAST(:bid AS uuid),
                    CAST(:ws AS uuid), CAST(:tid AS uuid), :amt)
            """,
            {
                "vid": plbv_id,
                "pid": plc_id,
                "bid": bundle_id,
                "ws": ws_id,
                "tid": tenant_id,
                "amt": supplier_amount,
            },
        )

        try:
            res = persist_market_deltas_for_workspace(wrap, ws_id)
            assert res.errors == [], res.errors
            assert res.updated >= 1, res

            wrap.execute(
                """
                SELECT market_delta_pct FROM price_line_bundle_values
                WHERE id = CAST(:id AS uuid)
                """,
                {"id": plbv_id},
            )
            row = wrap.fetchone()
            assert row is not None
            delta = float(row["market_delta_pct"])
            expected = float((supplier_amount - market_price) / market_price)
            assert abs(delta - expected) < 1e-6, (delta, expected)
        finally:
            _cleanup_v52_synthetic(
                wrap,
                ws_id=ws_id,
                tenant_id=tenant_id,
                case_id=case_id,
                committee_id=committee_id,
                eval_doc_id=None,
                bundle_id=bundle_id,
                crit_id=None,
                plc_id=plc_id,
                plbv_id=plbv_id,
                msv2_delete=True,
                item_id=item_id,
                zone_id=zone_id,
            )
            raw.close()


@pytest.mark.db
def test_r3_slug_matches_item_id_convention() -> None:
    """Sanity : item_id dict (souvent slug) reste aligné avec normalize_label."""
    assert normalize_label_to_item_slug("ciment_portland") == "ciment_portland"
