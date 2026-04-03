#!/usr/bin/env python3
"""
validate_dict_items.py — Phase 4 M15 / Validation items dictionnaire.

Passe label_status = 'draft' -> 'validated' sur les items confirmes.
Transaction atomique, rollback sur erreur.

Usage :
  python scripts/with_railway_env.py python scripts/validate_dict_items.py --input docs/data/dict_top100_to_validate.csv --dry-run
  python scripts/with_railway_env.py python scripts/validate_dict_items.py --input docs/data/dict_top100_to_validate.csv --apply --validated-by "CTO"

  Limiter le nombre d'items traites :
  python scripts/with_railway_env.py python scripts/validate_dict_items.py --input docs/data/dict_top100_to_validate.csv --apply --limit 20

Regles :
  - Ne modifie QUE label_status (jamais label_fr ni item_code)
  - Trigger trg_protect_item_identity : interdit modif label_fr si label_status='validated'
  - Si item deja 'validated' -> skip (idempotent)
  - Rollback complet sur erreur durant la transaction

Gate M15 : 100 items label_status='validated' avant premier run 100 dossiers.
"""

from __future__ import annotations

import argparse
import csv
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

GATE_MIN_VALIDATED = 100


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
        url, row_factory=dict_row, connect_timeout=20, autocommit=False
    )


def _normalize_value(v: str) -> str:
    """Supprime les retours a la ligne dans les valeurs CSV (champs multilignes)."""
    return v.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()


def load_csv(csv_path: Path) -> list[dict]:
    """Charge les items depuis le CSV de validation.

    Normalise les valeurs pour tolerer les CSV multilignes (label_fr avec retours ligne).
    """
    if not csv_path.exists():
        print(
            f"{RED}[ERR]{RESET} Fichier CSV introuvable : {csv_path}", file=sys.stderr
        )
        sys.exit(1)
    rows = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: _normalize_value(str(v)) for k, v in row.items()})
    return rows


def validate_items(
    item_ids: list[str],
    railway_url: str,
    validated_by: str,
    dry_run: bool = True,
) -> dict:
    # Copilot C1 : gerer la liste vide avant toute connexion
    results = {"validated": 0, "skipped_already": 0, "errors": 0, "dry_run": dry_run}
    if not item_ids:
        return results

    conn = _connect(railway_url)
    now = datetime.now(UTC).isoformat()

    try:
        with conn.cursor() as cur:
            # Copilot C1 : utiliser ANY(%s) — pas d'interpolation directe (SQL injection)
            cur.execute(
                "SELECT item_id, label_status FROM couche_b.procurement_dict_items "
                "WHERE item_id = ANY(%s)",
                (item_ids,),
            )
            current = {r["item_id"]: r["label_status"] for r in cur.fetchall()}

            to_validate = []
            for iid in item_ids:
                status = current.get(iid)
                if status == "validated":
                    results["skipped_already"] += 1
                elif status == "draft":
                    to_validate.append(iid)
                else:
                    print(
                        f"  {YELLOW}[SKIP]{RESET} item_id={iid} status={status} inattendu"
                    )

            print(
                f"  A valider : {len(to_validate)}, deja valides : {results['skipped_already']}"
            )

            if dry_run:
                print(f"  {YELLOW}[DRY-RUN]{RESET} Aucune ecriture.")
                conn.rollback()
                conn.close()
                results["would_validate"] = len(to_validate)
                return results

            # Validation en transaction
            for iid in to_validate:
                try:
                    # Modifier UNIQUEMENT label_status
                    cur.execute(
                        "UPDATE couche_b.procurement_dict_items "
                        "SET label_status = 'validated', "
                        "    validated_at = %s::timestamptz, "
                        "    validated_by = %s, "
                        "    human_validated = true "
                        "WHERE item_id = %s AND label_status = 'draft'",
                        (now, validated_by, iid),
                    )
                    updated = cur.rowcount
                    if updated == 0:
                        results["skipped_already"] += 1
                        continue

                    # Audit : validated_at, validated_by, human_validated suffisent.
                    # audit_log requiert prev_hash (blockchain) — hors perimetre M15.

                    results["validated"] += 1
                except Exception as exc:
                    print(f"  {RED}[ERR]{RESET} item_id={iid}: {exc}", file=sys.stderr)
                    results["errors"] += 1

            if results["errors"] > 0:
                print(f"  {RED}[ROLLBACK]{RESET} {results['errors']} erreur(s).")
                conn.rollback()
                conn.close()
                results["rolled_back"] = True
                return results

            # Gate check
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM couche_b.procurement_dict_items "
                "WHERE label_status = 'validated'"
            )
            total_validated = int(cur.fetchone()["cnt"])
            results["total_validated_post"] = total_validated
            results["gate_100_rempli"] = total_validated >= GATE_MIN_VALIDATED

            # Copilot C3 : le commit est toujours effectue — la gate est informationnelle,
            # pas un rollback (la validation partielle est intentionnellement conservee).
            # Un rollback ici annulerait les validations deja faites ce qui est pire.
            conn.commit()

    except Exception as exc:
        print(f"  {RED}[ERR]{RESET} Transaction : {exc}", file=sys.stderr)
        conn.rollback()
        raise
    finally:
        conn.close()

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valider items dictionnaire (Phase 4 M15)"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="CSV d'items a valider (ex: docs/data/dict_top100_to_validate.csv)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Simulation (defaut)"
    )
    parser.add_argument("--apply", action="store_true", help="Appliquer reellement")
    parser.add_argument(
        "--validated-by", default="CTO", help="Identifiant du validateur"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limiter le nombre d'items traites"
    )
    args = parser.parse_args()

    dry_run = not args.apply
    railway_url = _get_url()
    target = railway_url.split("@")[-1].split("/")[0] if "@" in railway_url else "?"

    print(f"\n{BOLD}VALIDATION DICT ITEMS Phase 4 M15{RESET}")
    print(f"Mode        : {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Cible       : {target}")
    print(f"Validateur  : {args.validated_by}")
    print()

    rows = load_csv(Path(args.input))
    if args.limit:
        rows = rows[: args.limit]
    print(f"  {len(rows)} items charges depuis {args.input}")

    item_ids = [r["item_id"] for r in rows if r.get("item_id")]

    result = validate_items(item_ids, railway_url, args.validated_by, dry_run=dry_run)

    print(f"\n{BOLD}Resultats :{RESET}")
    for k, v in result.items():
        print(f"  {k:35}: {v}")

    if not dry_run:
        total = result.get("total_validated_post", 0)
        gate_ok = result.get("gate_100_rempli", False)
        color = GREEN if gate_ok else YELLOW
        print(f"\n  {color}{BOLD}Gate M15-I2{RESET}")
        print(
            f"  {color}label_status=validated = {total} / {GATE_MIN_VALIDATED} requis{RESET}"
        )
        if not gate_ok:
            delta = GATE_MIN_VALIDATED - total
            print(
                f"  {YELLOW}Delta : {delta} items a valider avant premier run 100 dossiers{RESET}"
            )

        return 0 if gate_ok else 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
