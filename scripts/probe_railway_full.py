#!/usr/bin/env python3
"""
probe_railway_full.py — Phase 0 M15 / Probe Railway complet.

Execute les 9 requetes de probe avec les schemas corrects (issus des migrations)
et ecrit docs/PROBE_2026_04_03.md avec les resultats horodates.

Usage :
  python scripts/with_railway_env.py python scripts/probe_railway_full.py
  python scripts/with_railway_env.py python scripts/probe_railway_full.py --output docs/PROBE_2026_04_03.md

Schemas reels verifies sur Railway 2026-04-03 :
  couche_b.procurement_dict_items    (migration 005) — colonne label_status
  public.mercurials_item_map         (migration 040) — colonne dict_item_id (pas item_id)
  public.market_signals_v2           (migration 043) — colonne signal_quality
  public.market_surveys              (migration 042) — colonne date_surveyed
  public.zone_context_registry       (migration 042)
  public.annotation_registry         (migration ?) — colonne is_validated
  public.decision_snapshots          (migration 029)
  public.llm_traces                  (migration 065 — PENDING Railway)
  public.dms_event_index             (migration 061 — PENDING Railway)

ZERO ECRITURE — lecture seule. autocommit=True pour isolation par requete.
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
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _load_railway_env() -> str:
    url = os.environ.get("RAILWAY_DATABASE_URL", "")
    if not url:
        url = os.environ.get("DATABASE_URL", "")
    if not url:
        print(
            f"{RED}[ERR]{RESET} RAILWAY_DATABASE_URL absente. "
            "Lancer via : python scripts/with_railway_env.py python scripts/probe_railway_full.py",
            file=sys.stderr,
        )
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


def _scalar(cur, sql: str, params=None):
    cur.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        return 0
    return list(row.values())[0]


def _rows(cur, sql: str, params=None) -> list[dict]:
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def _table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        "SELECT to_regclass(%s) IS NOT NULL AS ex",
        (f"{schema}.{table}",),
    )
    return cur.fetchone()["ex"]  # type: ignore[index]


def run_probes(cur) -> list[dict]:
    results = []

    # P1 — Distribution label_status dictionnaire
    try:
        rows = _rows(
            cur,
            "SELECT label_status, COUNT(*) AS cnt "
            "FROM couche_b.procurement_dict_items GROUP BY label_status ORDER BY label_status",
        )
        dist = {r["label_status"]: int(r["cnt"]) for r in rows}
        validated_cnt = dist.get("validated", 0)
        results.append(
            {
                "id": "P1",
                "label": "Dict items par label_status",
                "status": "OK" if validated_cnt >= 100 else "WARN",
                "data": dist,
                "note": f"Gate M15 : 100 validated requis — actuellement {validated_cnt}",
            }
        )
    except Exception as exc:
        results.append(
            {
                "id": "P1",
                "label": "Dict items par label_status",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    # P2 — Couverture mercurials_item_map vs dict_items
    # Colonne reelle : dict_item_id (pas item_id)
    try:
        mapped = int(
            _scalar(
                cur,
                "SELECT COUNT(DISTINCT dict_item_id) FROM public.mercurials_item_map",
            )
        )
        total = int(
            _scalar(cur, "SELECT COUNT(*) FROM couche_b.procurement_dict_items")
        )
        pct = round(mapped * 100.0 / total, 2) if total else 0.0
        gate_ok = pct >= 70.0
        results.append(
            {
                "id": "P2",
                "label": "Couverture mercurials_item_map",
                "status": "OK" if gate_ok else "WARN",
                "data": {
                    "items_mapped": mapped,
                    "items_total": total,
                    "coverage_pct": pct,
                },
                "note": f"Gate signal engine : coverage >= 70% — actuellement {pct}%",
            }
        )
    except Exception as exc:
        results.append(
            {
                "id": "P2",
                "label": "Couverture mercurials_item_map",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    # P3 — Distribution signal_quality market_signals_v2
    try:
        rows = _rows(
            cur,
            "SELECT COALESCE(signal_quality,'NULL') AS sq, COUNT(*) AS cnt "
            "FROM public.market_signals_v2 GROUP BY sq ORDER BY cnt DESC",
        )
        dist = {r["sq"]: int(r["cnt"]) for r in rows}
        total_sig = sum(dist.values())
        strong_mod = dist.get("strong", 0) + dist.get("moderate", 0)
        pct_sm = round(strong_mod * 100.0 / total_sig, 2) if total_sig else 0.0
        gate_ok = pct_sm >= 40.0
        status = (
            "OK"
            if (gate_ok and total_sig > 0)
            else ("WARN" if total_sig > 0 else "EMPTY")
        )
        results.append(
            {
                "id": "P3",
                "label": "Distribution signal_quality market_signals_v2",
                "status": status,
                "data": {
                    "distribution": str(dist),
                    "total": total_sig,
                    "strong_moderate_pct": pct_sm,
                },
                "note": f"Gate M15 : strong+moderate >= 40% — actuellement {pct_sm}%",
            }
        )
    except Exception as exc:
        results.append(
            {
                "id": "P3",
                "label": "Distribution signal_quality",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    # P4 — Market surveys
    try:
        row = _rows(
            cur,
            "SELECT COUNT(*) AS cnt, MIN(date_surveyed) AS min_date, "
            "MAX(date_surveyed) AS max_date FROM public.market_surveys",
        )
        r = row[0] if row else {}
        cnt = int(r.get("cnt", 0))
        results.append(
            {
                "id": "P4",
                "label": "Market surveys",
                "status": "OK" if cnt > 0 else "EMPTY",
                "data": {
                    "count": cnt,
                    "min_date": str(r.get("min_date", "N/A")),
                    "max_date": str(r.get("max_date", "N/A")),
                },
                "note": "FormulaV11 poids 0.35 pour market_survey — vide = signal faible",
            }
        )
    except Exception as exc:
        results.append(
            {
                "id": "P4",
                "label": "Market surveys",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    # P5 — Zone context registry
    try:
        cnt = int(_scalar(cur, "SELECT COUNT(*) FROM public.zone_context_registry"))
        results.append(
            {
                "id": "P5",
                "label": "Zone context registry",
                "status": "OK" if cnt > 0 else "EMPTY",
                "data": {"count": cnt},
                "note": "Requis pour ajustements IPC saisonniers FormulaV11",
            }
        )
    except Exception as exc:
        results.append(
            {
                "id": "P5",
                "label": "Zone context registry",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    # P6 — Annotations (annotation_registry.is_validated + documents.extraction_status)
    # La vraie table d'annotation DMS = public.annotation_registry (is_validated)
    # extraction_jobs est vide sur Railway (pas le canal d'annotation)
    try:
        validated_count = int(
            _scalar(
                cur,
                "SELECT COUNT(*) FROM public.annotation_registry WHERE is_validated = true",
            )
        )
        total_annotations = int(
            _scalar(cur, "SELECT COUNT(*) FROM public.annotation_registry")
        )
        # Fallback : documents en pending (travail en attente d'extraction)
        docs_pending = int(
            _scalar(
                cur,
                "SELECT COUNT(*) FROM public.documents WHERE extraction_status = 'pending'",
            )
        )
        gate_ok = validated_count >= 50
        results.append(
            {
                "id": "P6",
                "label": "Annotations (annotation_registry + documents)",
                "status": "OK" if gate_ok else "WARN",
                "data": {
                    "annotation_registry_total": total_annotations,
                    "annotation_registry_validated": validated_count,
                    "documents_pending_extraction": docs_pending,
                    "gate_50_rempli": gate_ok,
                },
                "note": f"Gate REGLE-23 : is_validated >= 50 — actuellement {validated_count}. "
                f"87 annotations locales a synchroniser via Phase 2.",
            }
        )
    except Exception as exc:
        results.append(
            {
                "id": "P6",
                "label": "Annotations",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    # P7 — Decision snapshots (boucle feedback M14)
    try:
        cnt = int(_scalar(cur, "SELECT COUNT(*) FROM public.decision_snapshots"))
        results.append(
            {
                "id": "P7",
                "label": "Decision snapshots (feedback M14)",
                "status": "OK" if cnt > 0 else "EMPTY",
                "data": {"count": cnt},
                "note": "FormulaV11 poids 0.15 pour decision_history",
            }
        )
    except Exception as exc:
        results.append(
            {
                "id": "P7",
                "label": "Decision snapshots",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    # P8 — llm_traces (migration 065 — pending Railway pre-Phase 1)
    try:
        exists = _table_exists(cur, "public", "llm_traces")
        if exists:
            cnt = int(_scalar(cur, "SELECT COUNT(*) FROM public.llm_traces"))
            results.append(
                {
                    "id": "P8",
                    "label": "LLM traces (migration 065)",
                    "status": "OK",
                    "data": {"count": cnt},
                    "note": "Migration 065 deja appliquee",
                }
            )
        else:
            results.append(
                {
                    "id": "P8",
                    "label": "LLM traces (migration 065)",
                    "status": "PENDING_MIGRATION",
                    "data": {"count": "N/A — table absente"},
                    "note": "Table creee par migration 065 — appliquer Phase 1 d'abord",
                }
            )
    except Exception as exc:
        results.append(
            {
                "id": "P8",
                "label": "LLM traces",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    # P9 — dms_event_index (migration 061 — pending Railway pre-Phase 1)
    try:
        exists = _table_exists(cur, "public", "dms_event_index")
        if exists:
            cnt = int(_scalar(cur, "SELECT COUNT(*) FROM public.dms_event_index"))
            results.append(
                {
                    "id": "P9",
                    "label": "DMS event index (migration 061)",
                    "status": "OK",
                    "data": {"count": cnt},
                    "note": "Migration 061 deja appliquee",
                }
            )
        else:
            results.append(
                {
                    "id": "P9",
                    "label": "DMS event index (migration 061)",
                    "status": "PENDING_MIGRATION",
                    "data": {"count": "N/A — table absente"},
                    "note": "Table creee par migration 061 — appliquer Phase 1 d'abord",
                }
            )
    except Exception as exc:
        results.append(
            {
                "id": "P9",
                "label": "DMS event index",
                "status": "ERROR",
                "error": str(exc),
                "data": {},
            }
        )

    return results


def print_results(results: list[dict], target_label: str) -> int:
    warn_count = 0
    error_count = 0

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}PROBE RAILWAY FULL — {target_label}{RESET}")
    print(f"Date : {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"{'='*60}{RESET}")

    for r in results:
        pid = r["id"]
        label = r["label"]
        status = r["status"]
        data = r.get("data", {})
        note = r.get("note", "")
        err = r.get("error")

        if status == "OK":
            color = GREEN
        elif status in ("WARN", "EMPTY"):
            color = YELLOW
            warn_count += 1
        elif status == "PENDING_MIGRATION":
            color = BLUE
        else:
            color = RED
            error_count += 1

        print(f"\n  {color}[{pid}] {label}{RESET}")
        print(f"       Statut  : {color}{status}{RESET}")
        for k, v in (data.items() if isinstance(data, dict) else {}.items()):
            print(f"       {k:35}: {v}")
        if err:
            print(f"       {RED}Erreur : {err}{RESET}")
        if note:
            print(f"       {BLUE}Note   : {note}{RESET}")

    print(f"\n{'='*60}")
    if error_count > 0:
        print(
            f"{RED}{BOLD}VERDICT : {error_count} erreur(s) — corriger avant Phase 1{RESET}"
        )
    elif warn_count > 0:
        print(
            f"{YELLOW}{BOLD}VERDICT : {warn_count} warning(s) — voir notes ci-dessus{RESET}"
        )
    else:
        print(f"{GREEN}{BOLD}VERDICT : Probe OK — pret pour Phase 1{RESET}")
    print(f"{'='*60}\n")

    return error_count


def write_markdown(results: list[dict], target_label: str, output_path: Path) -> None:
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Probe Railway Full — Phase 0 M15",
        "",
        f"**Date :** {now}",
        f"**Cible :** `{target_label}`",
        "**Script :** `scripts/probe_railway_full.py`",
        "**Mode :** lecture seule (`autocommit=True`)",
        "",
        "---",
        "",
        "## Resume executif",
        "",
        "| ID | Libelle | Statut |",
        "|---|---|---|",
    ]
    for r in results:
        status_icon = {
            "OK": "VERT",
            "WARN": "ORANGE",
            "EMPTY": "ORANGE",
            "PENDING_MIGRATION": "BLEU",
            "ERROR": "ROUGE",
        }.get(r["status"], r["status"])
        lines.append(f"| {r['id']} | {r['label']} | {status_icon} |")

    lines += ["", "---", "", "## Details par probe", ""]
    for r in results:
        lines.append(f"### {r['id']} — {r['label']}")
        lines.append(f"- **Statut :** `{r['status']}`")
        data = r.get("data", {})
        if isinstance(data, dict):
            for k, v in data.items():
                lines.append(f"- **{k} :** `{v}`")
        if r.get("error"):
            lines.append(f"- **Erreur :** {r['error']}")
        if r.get("note"):
            lines.append(f"- **Note :** {r['note']}")
        lines.append("")

    # Extract key metrics for gates
    p1_data = next(
        (
            r["data"]
            for r in results
            if r["id"] == "P1" and "validated" in str(r.get("data", {}))
        ),
        {},
    )
    validated_100 = isinstance(p1_data, dict) and p1_data.get("validated", 0) >= 100

    p2_data = next((r["data"] for r in results if r["id"] == "P2"), {})
    cov_70 = isinstance(p2_data, dict) and float(p2_data.get("coverage_pct", 0)) >= 70

    p3_data = next((r["data"] for r in results if r["id"] == "P3"), {})
    sm_40 = (
        isinstance(p3_data, dict) and float(p3_data.get("strong_moderate_pct", 0)) >= 40
    )

    p6_data = next((r["data"] for r in results if r["id"] == "P6"), {})
    av_50 = isinstance(p6_data, dict) and bool(p6_data.get("gate_50_rempli", False))

    lines += [
        "---",
        "",
        "## Gates M15",
        "",
        "| Gate | Critere | Seuil | Etat |",
        "|---|---|---|---|",
        f"| REGLE-23 | annotation_registry.is_validated | >= 50 | {'VERT' if av_50 else 'ROUGE'} |",
        f"| M15-C3 | strong+moderate signal_quality | >= 40% | {'VERT' if sm_40 else 'ROUGE'} |",
        f"| M15-I2 | procurement_dict_items.validated | >= 100 | {'VERT' if validated_100 else 'ROUGE'} |",
        f"| Phase-3 | mercurials_item_map coverage | >= 70% | {'VERT' if cov_70 else 'ROUGE'} |",
        "",
        "---",
        "",
        "## Actions requises (Phase 1)",
        "",
        "1. **Appliquer migrations 059→067** : `python scripts/with_railway_env.py python scripts/apply_railway_migrations_safe.py --apply`",
        "2. **Synchroniser 87 annotations locales** : Phase 2 — `scripts/sync_annotations_local_to_railway.py`",
        "3. **Valider top 100 dict items** : Phase 4 — `scripts/validate_dict_items.py`",
        "4. **Mapping mercurials 67% → 70%** : Phase 3.1b — exporter `unmapped_items.csv`",
        "",
        "---",
        "",
        "*Genere automatiquement par `scripts/probe_railway_full.py`*",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{GREEN}[OK]{RESET} Rapport ecrit : {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Railway full — Phase 0 M15")
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "PROBE_2026_04_03.md"),
        help="Chemin du fichier Markdown de sortie",
    )
    args = parser.parse_args()

    url = _load_railway_env()
    target = url.split("@")[-1].split("/")[0] if "@" in url else url[:30]

    print(f"\n{BOLD}Connexion Railway : {target}{RESET}")
    conn = _connect(url)

    with conn.cursor() as cur:
        results = run_probes(cur)

    conn.close()

    error_count = print_results(results, target)
    write_markdown(results, target, Path(args.output))

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
