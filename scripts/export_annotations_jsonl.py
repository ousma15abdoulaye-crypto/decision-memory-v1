#!/usr/bin/env python3
"""
export_annotations_jsonl.py — V1 Activation Wartime M15.

Exporte public.annotation_registry depuis la DB locale vers un fichier JSONL
signe SHA256, pret pour import via sync_annotations_local_to_railway.py --from-jsonl.

Strategies (par ordre de preference) :
  1. Connexion directe via LOCAL_DATABASE_URL (si DB locale accessible)
  2. Lecture depuis CSV psql (--from-csv <fichier.csv>)
     Generer le CSV manuellement :
       psql -c "COPY public.annotation_registry TO STDOUT (FORMAT CSV, HEADER)" > annotations.csv

Usage :
  # Strategie 1 — DB locale accessible
  $env:LOCAL_DATABASE_URL = "postgresql://user:pass@localhost:5432/dms"
  python scripts/export_annotations_jsonl.py --output docs/data/annotations_export.jsonl

  # Strategie 2 — depuis CSV psql
  python scripts/export_annotations_jsonl.py --from-csv annotations.csv --output docs/data/annotations_export.jsonl

  # Verification seulement
  python scripts/export_annotations_jsonl.py --output docs/data/annotations_export.jsonl --verify

Output :
  docs/data/annotations_export.jsonl
    -> une ligne JSON par annotation, avec champ _sha256 de controle
    -> utilisable directement avec sync_annotations_local_to_railway.py --from-jsonl
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

ANNOTATION_REGISTRY_COLS = [
    "id",
    "document_id",
    "annotation_file",
    "sha256",
    "document_type",
    "annotated_by",
    "annotated_at",
    "duration_min",
    "field_count",
    "criteria_count",
    "is_validated",
    "validated_at",
    "created_at",
]


def _serialize(v) -> str | bool | int | float | None:
    """Serialise les types non-JSON (datetime, UUID)."""
    if v is None:
        return None
    if isinstance(v, uuid.UUID):
        return str(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v
    return str(v)


def _row_sha256(row: dict) -> str:
    """SHA256 deterministe d'un enregistrement."""
    stable = {k: str(row.get(k, "")) for k in sorted(ANNOTATION_REGISTRY_COLS)}
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


def export_from_db(local_url: str, output_path: Path) -> list[dict]:
    """Exporte depuis la DB locale via psycopg."""
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        print(f"{RED}[ERR]{RESET} psycopg non installe.", file=sys.stderr)
        sys.exit(2)

    url = local_url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )

    print(f"  Connexion DB locale : {url.split('@')[-1] if '@' in url else url[:40]}")
    try:
        conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)
    except Exception as exc:
        print(f"  {RED}[ERR]{RESET} Connexion echouee : {exc}", file=sys.stderr)
        print(
            f"  {YELLOW}[HINT]{RESET} Utiliser --from-csv avec export psql :\n"
            '    psql -c "COPY public.annotation_registry TO STDOUT (FORMAT CSV, HEADER)" > annotations.csv',
            file=sys.stderr,
        )
        sys.exit(3)

    with conn.cursor() as cur:
        cols = ", ".join(ANNOTATION_REGISTRY_COLS)
        cur.execute(
            f"SELECT {cols} FROM public.annotation_registry ORDER BY created_at"
        )
        rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    print(f"  {GREEN}[DB]{RESET} {len(rows)} annotation(s) lues.")
    return rows


def export_from_csv(csv_path: Path) -> list[dict]:
    """Charge les annotations depuis un CSV psql (COPY TO STDOUT FORMAT CSV HEADER)."""
    if not csv_path.exists():
        print(
            f"{RED}[ERR]{RESET} Fichier CSV introuvable : {csv_path}", file=sys.stderr
        )
        sys.exit(1)

    rows = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {}
            for k, v in raw.items():
                if k not in ANNOTATION_REGISTRY_COLS:
                    continue
                if v in ("", "\\N", "NULL"):
                    row[k] = None
                elif k in ("is_validated",):
                    row[k] = v.lower() in ("t", "true", "1", "yes")
                elif k in ("duration_min", "field_count", "criteria_count"):
                    try:
                        row[k] = int(v)
                    except (ValueError, TypeError):
                        row[k] = None
                else:
                    row[k] = v
            rows.append(row)

    print(f"  {GREEN}[CSV]{RESET} {len(rows)} annotation(s) chargees.")
    return rows


def write_jsonl(rows: list[dict], output_path: Path) -> None:
    """Ecrit les annotations en JSONL avec sha256 de controle."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validated_count = 0
    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            serialized = {k: _serialize(row.get(k)) for k in ANNOTATION_REGISTRY_COLS}
            serialized["_sha256"] = _row_sha256(serialized)
            f.write(json.dumps(serialized, ensure_ascii=False) + "\n")
            if row.get("is_validated") in (True, "t", "true", "1", "yes"):
                validated_count += 1

    print(f"  {GREEN}[JSONL]{RESET} Ecrit : {output_path}")
    print(f"  Total annotations     : {len(rows)}")
    print(f"  is_validated = true   : {validated_count}")
    print(f"  is_validated = false  : {len(rows) - validated_count}")


def verify_jsonl(path: Path) -> None:
    """Verifie l'integrite SHA256 du fichier JSONL."""
    ok = err = 0
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            obj = json.loads(line)
            expected = obj.pop("_sha256", None)
            actual = _row_sha256(obj)
            if expected == actual:
                ok += 1
            else:
                print(
                    f"  {RED}[ERR]{RESET} Ligne {i} : sha256 mismatch (id={obj.get('id')})"
                )
                err += 1
    color = GREEN if err == 0 else RED
    print(f"  {color}[VERIFY]{RESET} OK={ok} ERR={err}")
    if err:
        sys.exit(4)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export annotations locales -> JSONL (V1 Wartime M15)"
    )
    parser.add_argument(
        "--output",
        default="docs/data/annotations_export.jsonl",
        help="Fichier JSONL de sortie (defaut: docs/data/annotations_export.jsonl)",
    )
    parser.add_argument(
        "--from-csv",
        type=str,
        default=None,
        help="Charger depuis CSV psql au lieu de la DB locale",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verifier l'integrite SHA256 du JSONL (sans ecriture)",
    )
    args = parser.parse_args()

    output_path = ROOT / args.output

    print(f"\n{BOLD}EXPORT ANNOTATIONS LOCAL -> JSONL (V1 M15){RESET}")
    print(f"Sortie : {output_path}")
    print()

    if args.verify and output_path.exists():
        print(f"  {BLUE}[VERIFY]{RESET} Verification integrite SHA256...")
        verify_jsonl(output_path)
        return 0

    if args.from_csv:
        rows = export_from_csv(Path(args.from_csv))
    else:
        local_url = os.environ.get("LOCAL_DATABASE_URL", "")
        if not local_url:
            local_url = os.environ.get("DATABASE_URL", "")
        if not local_url:
            print(
                f"{RED}[ERR]{RESET} LOCAL_DATABASE_URL manquante.\n"
                "  Options :\n"
                "  1. Definir LOCAL_DATABASE_URL\n"
                "  2. Utiliser --from-csv <fichier.csv> apres export psql",
                file=sys.stderr,
            )
            return 2
        rows = export_from_db(local_url, output_path)

    if not rows:
        print(f"{YELLOW}[WARN]{RESET} Aucune annotation trouvee.")
        return 0

    write_jsonl(rows, output_path)
    verify_jsonl(output_path)

    print(f"\n{BOLD}Prochaine etape :{RESET}")
    print(
        f"  python scripts/with_railway_env.py python scripts/sync_annotations_local_to_railway.py "
        f"--from-jsonl {args.output} --apply"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
