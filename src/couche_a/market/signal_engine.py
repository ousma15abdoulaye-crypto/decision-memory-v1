"""
Signal Engine M9 -- orchestrateur.

Schema reel confirme probe ETAPE 0 :
  mercurials.year INTEGER (pas de mois)
  mercurials.price_avg NUMERIC
  mercurials.zone_id TEXT
  mercurials.item_id UUID NULL -- jointure via mercurials_item_map
  decision_history : ABSENTE
  market_surveys.item_id TEXT, date_surveyed DATE, price_per_unit NUMERIC

Chemin jointure mercurials -> dict_items :
  Via public.mercurials_item_map (item_canonical -> dict_item_id)
  1629 mappings confirmes Railway.
"""

from __future__ import annotations

import json
import logging

import psycopg
from psycopg.rows import dict_row

from .formula_v11 import (
    ContextSnapshot,
    FormulaV11,
    FORMULA_VERSION,
    PricePoint,
    SignalResult,
)

logger = logging.getLogger(__name__)

# ── Freshness mercuriale -- regle ADR section 2 ──────────────────────────────
# age_months = (CURRENT_YEAR - year) * 12
# Annee courante -> 0 -> f=1.00
# Annee N-1     -> 12 -> f=0.30 (FRESHNESS_OLD)
_MERC_CURRENT_YEAR_CUTOFF = 0


class SignalEngine:
    def __init__(self, db_url: str):
        if not db_url:
            raise ValueError("DATABASE_URL requis")
        if "railway" in db_url.lower():
            raise ValueError("CONTRACT-02")
        self.db_url = (
            db_url.replace("postgresql+psycopg://", "postgresql://")
            .replace("postgresql+psycopg2://", "postgresql://")
        )
        self.formula = FormulaV11()

    def _conn(self) -> psycopg.Connection:
        return psycopg.connect(self.db_url, row_factory=dict_row)

    def get_context(
        self,
        cur: psycopg.Cursor,
        zone_id: str,
        month: int | None = None,
        taxo_l3: str | None = None,
    ) -> ContextSnapshot:
        cur.execute(
            """
            SELECT context_type, severity_level,
                   structural_markup_pct
            FROM public.zone_context_registry
            WHERE zone_id    = %s
              AND valid_from <= CURRENT_DATE
              AND (valid_until IS NULL
                   OR valid_until >= CURRENT_DATE)
            ORDER BY valid_from DESC LIMIT 1
            """,
            (zone_id,),
        )
        ctx = cur.fetchone()
        markup = 0.0
        ct = "normal"
        severity = "ipc_1_minimal"
        if ctx:
            markup = float(ctx["structural_markup_pct"] or 0)
            ct = ctx["context_type"]
            severity = ctx["severity_level"]

        seasonal = 0.0
        if month and taxo_l3:
            cur.execute(
                """
                SELECT historical_deviation_pct, confidence
                FROM public.seasonal_patterns
                WHERE zone_id = %s
                  AND taxo_l3 = %s
                  AND month   = %s
                  AND superseded_by IS NULL
                ORDER BY COALESCE(confidence, 0) DESC,
                         computation_version DESC
                LIMIT 1
                """,
                (zone_id, taxo_l3, month),
            )
            sp = cur.fetchone()
            if sp:
                seasonal = float(sp["historical_deviation_pct"] or 0)

        return ContextSnapshot(
            context_type=ct,
            severity_level=severity,
            structural_markup_pct=markup,
            seasonal_deviation_pct=seasonal,
        )

    def get_price_points(
        self,
        cur: psycopg.Cursor,
        item_id: str,
        zone_id: str,
    ) -> list[PricePoint]:
        points: list[PricePoint] = []
        current_year = None

        # Source 1 : mercuriales via mercurials_item_map
        try:
            cur.execute(
                """
                SELECT m.price_avg AS prix, m.year
                FROM mercurials m
                JOIN public.mercurials_item_map map
                  ON map.item_canonical = m.item_canonical
                WHERE map.dict_item_id = %s
                  AND m.zone_id = %s
                  AND m.price_avg > 0
                  AND m.year >= EXTRACT(YEAR FROM CURRENT_DATE)::int - 1
                ORDER BY m.year DESC
                """,
                (item_id, zone_id),
            )
            for r in cur.fetchall():
                if current_year is None:
                    cur.execute("SELECT EXTRACT(YEAR FROM CURRENT_DATE)::int AS y")
                    current_year = cur.fetchone()["y"]
                # ADR section 2 : freshness mercuriale = (current_year - year) * 12
                age_months = min((current_year - r["year"]) * 12, 12)
                age_months = max(age_months, 0)
                if r["prix"]:
                    points.append(
                        PricePoint(
                            price=float(r["prix"]),
                            source_type="mercuriale_official",
                            age_months=age_months,
                        )
                    )
        except Exception as e:
            logger.warning("mercurials join failed item=%s: %s", item_id, e)

        # Source 2 : surveys valides
        try:
            cur.execute(
                """
                SELECT price_per_unit AS prix,
                       GREATEST(0, LEAST(4,
                         EXTRACT(MONTH FROM
                           AGE(CURRENT_DATE, date_surveyed))::int
                       )) AS age
                FROM public.market_surveys
                WHERE item_id           = %s
                  AND zone_id           = %s
                  AND validation_status = 'validated'
                  AND price_per_unit IS NOT NULL
                  AND price_per_unit > 0
                  AND date_surveyed >= CURRENT_DATE - INTERVAL '4 months'
                ORDER BY date_surveyed DESC
                """,
                (item_id, zone_id),
            )
            for r in cur.fetchall():
                points.append(
                    PricePoint(
                        price=float(r["prix"]),
                        source_type="market_survey",
                        age_months=int(r["age"]),
                    )
                )
        except Exception as e:
            logger.warning("market_surveys query failed: %s", e)

        # Source 3 : decision_history (absente -- contribution 0)
        # Quand la table sera creee, le moteur la consommera automatiquement.

        return points

    def try_propagate(
        self,
        cur: psycopg.Cursor,
        item_id: str,
        zone_id: str,
    ) -> SignalResult | None:
        cur.execute(
            """
            SELECT zone_from, transport_markup,
                   crisis_multiplier, reliability
            FROM public.geo_price_corridors
            WHERE zone_to    = %s
              AND reliability IS NOT NULL
            ORDER BY reliability DESC LIMIT 1
            """,
            (zone_id,),
        )
        corridor = cur.fetchone()
        if not corridor:
            return None

        src_zone = corridor["zone_from"]
        t_markup = float(corridor["transport_markup"])
        c_mult = float(corridor["crisis_multiplier"])

        src_pts = self.get_price_points(cur, item_id, src_zone)
        if not src_pts:
            return None

        src_ctx = self.get_context(cur, src_zone)
        src_res = self.formula.compute(item_id, src_zone, src_pts, src_ctx)
        if not src_res.price_raw:
            return None

        prop_price = src_res.price_raw * t_markup * c_mult
        dst_ctx = self.get_context(cur, zone_id)
        return self.formula.compute(
            item_id,
            zone_id,
            [
                PricePoint(
                    price=prop_price, source_type="mercuriale_official", age_months=0
                )
            ],
            dst_ctx,
            propagated_from=src_zone,
        )

    def compute_signal(
        self,
        item_id: str,
        zone_id: str,
        month: int | None = None,
        taxo_l3: str | None = None,
    ) -> SignalResult:
        conn = self._conn()
        cur = conn.cursor()
        try:
            ctx = self.get_context(cur, zone_id, month, taxo_l3)
            points = self.get_price_points(cur, item_id, zone_id)
            if not points:
                prop = self.try_propagate(cur, item_id, zone_id)
                return prop or SignalResult(item_id=item_id, zone_id=zone_id)
            return self.formula.compute(item_id, zone_id, points, ctx)
        finally:
            conn.close()

    def persist_signal(
        self,
        result: SignalResult,
        conn: psycopg.Connection | None = None,
    ) -> None:
        close = conn is None
        if conn is None:
            conn = self._conn()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO public.market_signals_v2 (
                    item_id, zone_id, price_avg,
                    price_crisis_adj, price_seasonal_adj,
                    residual_pct, alert_level, signal_quality,
                    formula_version,
                    structural_markup_applied,
                    seasonal_deviation_applied,
                    context_type_at_computation,
                    source_mercuriale_count,
                    source_survey_count,
                    source_decision_count,
                    is_propagated, propagated_from_zone,
                    updated_at
                ) VALUES (
                    %(item_id)s, %(zone_id)s, %(price_raw)s,
                    %(price_crisis_adj)s, %(price_seasonal_adj)s,
                    %(residual_pct)s, %(alert_level)s, %(signal_quality)s,
                    %(formula_version)s,
                    %(structural_markup_applied)s,
                    %(seasonal_deviation_applied)s,
                    %(context_type_at_computation)s,
                    %(source_mercuriale_count)s,
                    %(source_survey_count)s,
                    %(source_decision_count)s,
                    %(is_propagated)s, %(propagated_from_zone)s,
                    now()
                )
                ON CONFLICT (item_id, zone_id) DO UPDATE SET
                    price_avg    = EXCLUDED.price_avg,
                    price_crisis_adj    = EXCLUDED.price_crisis_adj,
                    price_seasonal_adj  = EXCLUDED.price_seasonal_adj,
                    residual_pct        = EXCLUDED.residual_pct,
                    alert_level         = EXCLUDED.alert_level,
                    signal_quality      = EXCLUDED.signal_quality,
                    structural_markup_applied   =
                        EXCLUDED.structural_markup_applied,
                    seasonal_deviation_applied  =
                        EXCLUDED.seasonal_deviation_applied,
                    context_type_at_computation =
                        EXCLUDED.context_type_at_computation,
                    source_mercuriale_count = EXCLUDED.source_mercuriale_count,
                    source_survey_count     = EXCLUDED.source_survey_count,
                    source_decision_count   = EXCLUDED.source_decision_count,
                    is_propagated       = EXCLUDED.is_propagated,
                    propagated_from_zone = EXCLUDED.propagated_from_zone,
                    updated_at          = now()
                """,
                {
                    "item_id": result.item_id,
                    "zone_id": result.zone_id,
                    "formula_version": FORMULA_VERSION,
                    "price_raw": result.price_raw,
                    "price_crisis_adj": result.price_crisis_adj,
                    "price_seasonal_adj": result.price_seasonal_adj,
                    "residual_pct": result.residual_pct,
                    "alert_level": result.alert_level,
                    "signal_quality": result.signal_quality,
                    "structural_markup_applied": result.structural_markup_applied,
                    "seasonal_deviation_applied": result.seasonal_deviation_applied,
                    "context_type_at_computation": result.context_type_at_computation,
                    "source_mercuriale_count": result.source_mercuriale_count,
                    "source_survey_count": result.source_survey_count,
                    "source_decision_count": result.source_decision_count,
                    "is_propagated": result.is_propagated,
                    "propagated_from_zone": result.propagated_from_zone,
                },
            )
            # Log immuable
            cur.execute(
                """
                INSERT INTO public.signal_computation_log (
                    item_id, zone_id, formula_version,
                    price_raw, price_crisis_adj, price_seasonal_adj,
                    residual_pct, alert_level, signal_quality,
                    source_count, sources_detail, context_snapshot
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    result.item_id,
                    result.zone_id,
                    FORMULA_VERSION,
                    result.price_raw,
                    result.price_crisis_adj,
                    result.price_seasonal_adj,
                    result.residual_pct,
                    result.alert_level,
                    result.signal_quality,
                    (
                        result.source_mercuriale_count
                        + result.source_survey_count
                        + result.source_decision_count
                    ),
                    json.dumps(
                        {
                            "mercuriale": result.source_mercuriale_count,
                            "survey": result.source_survey_count,
                            "decision": result.source_decision_count,
                        }
                    ),
                    json.dumps(
                        {
                            "context_type": result.context_type_at_computation,
                            "markup_pct": result.structural_markup_applied,
                            "seasonal_pct": result.seasonal_deviation_applied,
                        }
                    ),
                ),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(
                "persist_signal failed item=%s zone=%s: %s",
                result.item_id,
                result.zone_id,
                e,
            )
            raise
        finally:
            if close:
                conn.close()
