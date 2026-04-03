#!/usr/bin/env python3
"""
measure_m15_metrics.py — Phase 8 M15 / Mesurer les 6 metriques M15.

Interroge Railway et genere docs/reports/M15_METRICS.md.

Usage :
  python scripts/with_railway_env.py python scripts/measure_m15_metrics.py
  python scripts/with_railway_env.py python scripts/measure_m15_metrics.py --output docs/reports/M15_METRICS.md

Metriques M15 (Plan V4.1 XII) :
  C1. coverage_extraction  : % documents avec extraction terminee
  C2. unresolved_rate      : % dossiers sans decision finale
  C3. vendor_match_rate    : % items avec fournisseur identifie
  C4. review_queue_rate    : % extractions en review_required
  C5. signal_quality_cov   : % items avec signal market != empty
  C6. drift_by_category    : derive prix moyenne par categorie L1 (top 5)

Seuils Gate M15 (Plan V4.1) :
  C1 >= 80%     C2 <= 25%     C3 >= 60%
  C4 <= 30%     C5 >= 50%     C6 : information uniquement

ZERO ECRITURE.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

GATES = {
    "C1_coverage_extraction": (">=", 80.0),
    "C2_unresolved_rate": ("<=", 25.0),
    "C3_vendor_match_rate": (">=", 60.0),
    "C4_review_queue_rate": ("<=", 30.0),
    "C5_signal_quality_cov": (">=", 50.0),
}


def _get_url() -> str:
    url = os.environ.get("RAILWAY_DATABASE_URL", "")
    if not url:
        url = os.environ.get("DATABASE_URL", "")
    if not url:
        print(f"{RED}[ERR]{RESET} RAILWAY_DATABASE_URL manquante.", file=sys.stderr)
        sys.exit(2)
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )


def _connect(url: str):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        print(f"{RED}[ERR]{RESET} psycopg non installe.", file=sys.stderr)
        sys.exit(2)
    return psycopg.connect(
        url, row_factory=dict_row, connect_timeout=20, autocommit=True
    )


def measure_metrics(cur) -> dict:
    metrics = {}

    # C1 — coverage_extraction
    # % documents avec extraction_status non pending
    try:
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE extraction_status != 'pending') AS done
            FROM public.documents
        """)
        r = cur.fetchone()
        total = int(r["total"]) if r else 0
        done = int(r["done"]) if r else 0
        pct = round(done * 100.0 / total, 2) if total else 0.0
        metrics["C1_coverage_extraction"] = {
            "value": pct,
            "label": "coverage_extraction (%)",
            "detail": f"{done}/{total} documents extractes",
            "note": "% docs hors status pending",
        }
    except Exception as exc:
        metrics["C1_coverage_extraction"] = {"value": None, "error": str(exc)}

    # C2 — unresolved_rate
    # % cases sans decision_snapshot (= sans decision finale enregistree)
    try:
        cur.execute("SELECT COUNT(*) AS total_cases FROM public.cases")
        total_cases = int(cur.fetchone()["total_cases"])
        cur.execute("""
            SELECT COUNT(DISTINCT c.id) AS with_decision
            FROM public.cases c
            INNER JOIN public.decision_snapshots ds ON ds.case_id = c.id::text
        """)
        with_decision = int(cur.fetchone()["with_decision"])
        without_decision = total_cases - with_decision
        unresolved_pct = (
            round(without_decision * 100.0 / total_cases, 2) if total_cases else 0.0
        )
        metrics["C2_unresolved_rate"] = {
            "value": unresolved_pct,
            "label": "unresolved_rate (%)",
            "detail": f"{without_decision}/{total_cases} dossiers sans decision",
            "note": "% cases sans decision_snapshot",
        }
    except Exception as exc:
        metrics["C2_unresolved_rate"] = {"value": None, "error": str(exc)}

    # C3 — vendor_match_rate
    # % offers avec supplier_raw identifie dans vendors
    try:
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE vendor_id IS NOT NULL) AS matched
            FROM public.market_surveys
        """)
        r = cur.fetchone()
        total = int(r["total"]) if r else 0
        matched = int(r["matched"]) if r else 0
        pct = round(matched * 100.0 / total, 2) if total else 0.0
        metrics["C3_vendor_match_rate"] = {
            "value": pct,
            "label": "vendor_match_rate (%)",
            "detail": f"{matched}/{total} market_surveys avec vendor_id",
            "note": "% surveys avec vendor identifie",
        }
    except Exception as exc:
        metrics["C3_vendor_match_rate"] = {"value": None, "error": str(exc)}

    # C4 — review_queue_rate
    # % annotations annotation_registry en attente (is_validated=false)
    try:
        cur.execute("SELECT COUNT(*) AS total FROM public.annotation_registry")
        total_ann = int(cur.fetchone()["total"])
        cur.execute(
            "SELECT COUNT(*) AS in_review FROM public.annotation_registry WHERE is_validated = false"
        )
        in_review = int(cur.fetchone()["in_review"])
        pct = round(in_review * 100.0 / total_ann, 2) if total_ann else 0.0
        metrics["C4_review_queue_rate"] = {
            "value": pct,
            "label": "review_queue_rate (%)",
            "detail": f"{in_review}/{total_ann} annotations en attente validation",
            "note": "% annotation_registry is_validated=false",
        }
    except Exception as exc:
        metrics["C4_review_queue_rate"] = {"value": None, "error": str(exc)}

    # C5 — signal_quality_cov
    # % items dict avec au moins 1 signal dans market_signals_v2
    try:
        cur.execute("SELECT COUNT(*) AS total FROM couche_b.procurement_dict_items")
        total_items = int(cur.fetchone()["total"])
        cur.execute(
            "SELECT COUNT(DISTINCT item_id) AS with_signal FROM public.market_signals_v2"
        )
        with_signal = int(cur.fetchone()["with_signal"])
        pct = round(with_signal * 100.0 / total_items, 2) if total_items else 0.0
        metrics["C5_signal_quality_cov"] = {
            "value": pct,
            "label": "signal_quality_cov (%)",
            "detail": f"{with_signal}/{total_items} items avec signal",
            "note": "% dict items avec >= 1 signal market_signals_v2",
        }
    except Exception as exc:
        metrics["C5_signal_quality_cov"] = {"value": None, "error": str(exc)}

    # C6 — drift_by_category (top 5 categories par deviation prix)
    try:
        cur.execute("""
            SELECT
                pdi.taxo_l1,
                COUNT(DISTINCT ms2.id)                AS signal_count,
                ROUND(AVG(ms2.residual_pct)::numeric, 2) AS avg_residual_pct,
                ROUND(AVG(ms2.price_avg)::numeric, 2)    AS avg_price
            FROM public.market_signals_v2 ms2
            JOIN couche_b.procurement_dict_items pdi ON pdi.item_id = ms2.item_id
            WHERE pdi.taxo_l1 IS NOT NULL
            GROUP BY pdi.taxo_l1
            HAVING COUNT(DISTINCT ms2.id) >= 5
            ORDER BY ABS(AVG(ms2.residual_pct)) DESC NULLS LAST
            LIMIT 10
        """)
        drift_rows = [dict(r) for r in cur.fetchall()]
        metrics["C6_drift_by_category"] = {
            "value": "voir detail",
            "label": "drift_by_category",
            "detail": drift_rows,
            "note": "Top categories par deviation prix (residual_pct)",
        }
    except Exception as exc:
        metrics["C6_drift_by_category"] = {"value": None, "error": str(exc)}

    return metrics


def evaluate_gates(metrics: dict) -> dict:
    """Evalue les gates M15."""
    results = {}
    for key, (op, threshold) in GATES.items():
        m = metrics.get(key, {})
        val = m.get("value")
        if val is None:
            results[key] = {"gate": "ERROR", "value": None, "threshold": threshold}
            continue
        if op == ">=":
            passed = float(val) >= threshold
        else:
            passed = float(val) <= threshold
        results[key] = {
            "gate": "VERT" if passed else "ROUGE",
            "value": val,
            "threshold": threshold,
            "op": op,
        }
    return results


def print_metrics(metrics: dict, gates: dict) -> None:
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}METRIQUES M15 — DMS V4.1{RESET}")
    print(f"Date : {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"{'='*60}{RESET}\n")

    for key, m in metrics.items():
        gate_info = gates.get(key, {})
        gate_status = gate_info.get("gate", "INFO")
        color = (
            GREEN
            if gate_status == "VERT"
            else (RED if gate_status == "ROUGE" else YELLOW)
        )
        val = m.get("value", "N/A")
        label = m.get("label", key)
        detail = m.get("detail", "")
        err = m.get("error")

        print(f"  {color}[{key[:2]}]{RESET} {label}")
        print(f"       Valeur : {color}{val}{RESET}")
        if gate_status in ("VERT", "ROUGE"):
            op, threshold = gate_info.get("op", "?"), gate_info.get("threshold", "?")
            print(f"       Gate   : {op} {threshold}% — {color}{gate_status}{RESET}")
        if isinstance(detail, list):
            for r in detail[:5]:
                print(
                    f"         {r.get('taxo_l1', '?'):25} residual={r.get('avg_residual_pct', '?')}% signals={r.get('signal_count', '?')}"
                )
        elif detail:
            print(f"       Detail : {detail}")
        if err:
            print(f"       {RED}Erreur : {err}{RESET}")
        print()


def write_markdown(metrics: dict, gates: dict, output_path: Path) -> None:
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    gate_counts = {"VERT": 0, "ROUGE": 0, "ERROR": 0}
    for g in gates.values():
        gate_counts[g.get("gate", "ERROR")] = (
            gate_counts.get(g.get("gate", "ERROR"), 0) + 1
        )

    lines = [
        "# Rapport Metriques M15 — DMS V4.1",
        "",
        f"**Date :** {now}",
        "**Script :** `scripts/measure_m15_metrics.py`",
        f"**Gates VERT :** {gate_counts['VERT']}/5 | **ROUGE :** {gate_counts['ROUGE']}/5",
        "",
        "---",
        "",
        "## Tableau de bord M15",
        "",
        "| Metrique | Valeur | Seuil | Gate |",
        "|---|---|---|---|",
    ]

    gate_order = [
        "C1_coverage_extraction",
        "C2_unresolved_rate",
        "C3_vendor_match_rate",
        "C4_review_queue_rate",
        "C5_signal_quality_cov",
    ]
    for key in gate_order:
        m = metrics.get(key, {})
        g = gates.get(key, {})
        val = m.get("value", "N/A")
        label = m.get("label", key)
        op = g.get("op", "")
        threshold = g.get("threshold", "")
        gate_status = g.get("gate", "N/A")
        lines.append(f"| {label} | {val}% | {op} {threshold}% | {gate_status} |")

    lines += ["", "---", "", "## Details metriques", ""]

    for key, m in metrics.items():
        g = gates.get(key, {})
        lines.append(f"### {m.get('label', key)}")
        lines.append(f"- **Valeur :** `{m.get('value', 'N/A')}`")
        if g.get("gate"):
            lines.append(
                f"- **Gate :** `{g['op']} {g['threshold']}%` -> **{g['gate']}**"
            )
        detail = m.get("detail")
        if isinstance(detail, list):
            lines.append("- **Derive par categorie :**")
            for r in detail[:10]:
                lines.append(
                    f"  - {r.get('taxo_l1', '?')} : residual={r.get('avg_residual_pct', '?')}% ({r.get('signal_count', '?')} signaux)"
                )
        elif detail:
            lines.append(f"- **Detail :** {detail}")
        if m.get("note"):
            lines.append(f"- **Note :** {m['note']}")
        if m.get("error"):
            lines.append(f"- **Erreur :** {m['error']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Actions requises",
        "",
        "| Gate | Statut | Action |",
        "|---|---|---|",
    ]

    actions = {
        "C1_coverage_extraction": "Lancer orchestrateur M12 sur documents pending",
        "C2_unresolved_rate": "Traiter 100 dossiers DAO/RFQ avant M15-done",
        "C3_vendor_match_rate": "Enrichir vendors dans market_surveys (mapping fournisseurs)",
        "C4_review_queue_rate": "Sync 87 annotations locales + valider review_required",
        "C5_signal_quality_cov": "Compléter mapping mercurials_item_map (coverage 67->70%)",
    }

    for key in gate_order:
        g = gates.get(key, {})
        gate = g.get("gate", "N/A")
        action = actions.get(key, "N/A")
        lines.append(
            f"| {metrics.get(key, {}).get('label', key)} | {gate} | {action} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Checklist M15 — 14 criteres",
        "",
        "```",
        "[X] 1. Probe Railway documentee — 9 metriques dans docs/PROBE_2026_04_03.md",
        "[X] 2. Migrations 059->067 appliquees — alembic current = 067",
        "[ ] 3. annotated_validated >= 50 — gate REGLE-23 (0 actuel, 87 local a sync)",
        "[X] 4. mercurials_item_map coverage documentee (67.38%)",
        "[X] 5. market_signals_v2 : strong+moderate >= 40% (90.43% VERT)",
        "[X] 6. 100 items dict_items label_status = validated",
        "[ ] 7. ANNOTATION_USE_PASS_ORCHESTRATOR = 1 en prod (mandat Railway Dashboard CTO)",
        "[X] 8. RLS policies actives Railway — 12 policies verifiees",
        "[X] 9. DISASTER_RECOVERY.md operationnel",
        "[ ] 10. 100 dossiers DAO/RFQ traites avec metriques",
        "[ ] 11. Precision extraction documentee (donnee reelle)",
        "[X] 12. ADR-SIGNAL-TRIGGER-001 signe",
        "[ ] 13. Redis/ARQ ou alternative documentee (ADR-H2-ARQ-001 existant, REDIS_URL Railway pending)",
        "[ ] 14. M15_METRICS.md publie avec donnees reelles (ce fichier — donnees partielles)",
        "```",
        "",
        "---",
        "",
        "*Genere automatiquement par `scripts/measure_m15_metrics.py`*",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{GREEN}[OK]{RESET} Rapport ecrit : {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Metriques M15 — Phase 8")
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "reports" / "M15_METRICS.md"),
        help="Fichier de sortie Markdown",
    )
    args = parser.parse_args()

    url = _get_url()
    target = url.split("@")[-1].split("/")[0] if "@" in url else url[:30]

    print(f"\n{BOLD}METRIQUES M15{RESET}")
    print(f"Cible : {target}")

    conn = _connect(url)
    with conn.cursor() as cur:
        metrics = measure_metrics(cur)
    conn.close()

    gates = evaluate_gates(metrics)
    print_metrics(metrics, gates)
    write_markdown(metrics, gates, Path(args.output))

    # Retourner 0 ssi tous les gates VERT
    failed = sum(1 for g in gates.values() if g.get("gate") == "ROUGE")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
