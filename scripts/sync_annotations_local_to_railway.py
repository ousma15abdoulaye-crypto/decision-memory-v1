#!/usr/bin/env python3
"""
sync_annotations_local_to_railway.py — Phase 2 M15 / Sync annotations locales → Railway.

Synchronise les enregistrements de public.annotation_registry depuis la base locale
vers Railway. Insert-only (ON CONFLICT DO NOTHING) en transaction atomique,
rollback sur erreur SQL, gate REGLE-23 post-sync.
Note : les enregistrements deja presents sur Railway ne sont pas mis a jour (pas d'UPSERT).
Pour detecter des divergences, consulter les logs "deja presentes" en sortie.

Usage :
  # Configurer les URLs (si DATABASE_URL n'est pas la bonne URL locale) :
  $env:LOCAL_DATABASE_URL = "postgresql://user:pass@localhost:5432/dbname"
  python scripts/with_railway_env.py python scripts/sync_annotations_local_to_railway.py --dry-run
  python scripts/with_railway_env.py python scripts/sync_annotations_local_to_railway.py --apply

  # Ou via JSONL (si DB locale inaccessible) :
  python scripts/with_railway_env.py python scripts/sync_annotations_local_to_railway.py --from-jsonl annotations_export.jsonl --apply

Variables d'env requises :
  LOCAL_DATABASE_URL  : URL de la DB locale (ou DATABASE_URL si unique)
  RAILWAY_DATABASE_URL : URL Railway (chargee par with_railway_env.py)

Statuts importes :
  is_validated=true  → sync prioritaire
  is_validated=false → sync (annotations en attente de validation)

Gate REGLE-23 post-sync : annotation_registry.is_validated >= 50

ZERO ECRITURE en dry-run. --apply requis pour toucher Railway.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

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

GATE_MIN_VALIDATED = 50


def _assert_safe_local_url(local_url: str) -> None:
    """Refuse d'utiliser une URL non-locale comme source sauf opt-in explicite.

    Reprend le meme pattern de securite que sync_dict_local_to_railway.py pour
    eviter d'acceder a Railway en pensant lire depuis local.
    """
    hostname = urlparse(local_url).hostname or ""
    is_local = hostname in ("localhost",) or hostname.startswith("127.")
    if not is_local:
        if os.getenv("DMS_ALLOW_RAILWAY_SYNC") != "1":
            raise RuntimeError(
                f"URL locale suspecte ({hostname!r}) : ne pointe pas vers localhost/127.x. "
                "Definir DMS_ALLOW_RAILWAY_SYNC=1 pour forcer."
            )


def _get_local_url() -> str:
    """Retourne l'URL de la DB locale avec guard de securite."""
    url = os.environ.get("LOCAL_DATABASE_URL", "")
    if not url:
        url = os.environ.get("DATABASE_URL", "")
    if not url:
        print(
            f"{RED}[ERR]{RESET} LOCAL_DATABASE_URL ou DATABASE_URL manquante.\n"
            "  Exemple : $env:LOCAL_DATABASE_URL = 'postgresql://user:pass@localhost:5432/dms'",
            file=sys.stderr,
        )
        sys.exit(2)
    url = url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )
    _assert_safe_local_url(url)
    return url


def _get_railway_url() -> str:
    url = os.environ.get("RAILWAY_DATABASE_URL", "")
    if not url:
        print(
            f"{RED}[ERR]{RESET} RAILWAY_DATABASE_URL manquante. "
            "Lancer via : python scripts/with_railway_env.py ...",
            file=sys.stderr,
        )
        sys.exit(2)
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )


def _connect(url: str, autocommit: bool = False):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        print(f"{RED}[ERR]{RESET} psycopg non installe.", file=sys.stderr)
        sys.exit(2)
    return psycopg.connect(
        url, row_factory=dict_row, connect_timeout=20, autocommit=autocommit
    )


def _row_sha256(row: dict) -> str:
    """Calcule le SHA256 deterministe d'un enregistrement (pour deduplication)."""
    stable = {k: str(row.get(k, "")) for k in sorted(ANNOTATION_REGISTRY_COLS)}
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def fetch_local_annotations(local_url: str) -> list[dict]:
    """Extrait les annotations depuis la DB locale."""
    try:
        conn = _connect(local_url, autocommit=True)
        with conn.cursor() as cur:
            cols = ", ".join(ANNOTATION_REGISTRY_COLS)
            cur.execute(
                f"SELECT {cols} FROM public.annotation_registry ORDER BY created_at"
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        print(f"  {GREEN}[LOCAL]{RESET} {len(rows)} annotation(s) trouvees.")
        return rows
    except Exception as exc:
        print(
            f"  {RED}[ERR]{RESET} Connexion locale impossible : {exc}", file=sys.stderr
        )
        print(
            f"  {YELLOW}[HINT]{RESET} Definir LOCAL_DATABASE_URL avec les bons credentials.",
            file=sys.stderr,
        )
        return []


def fetch_from_jsonl(jsonl_path: Path) -> list[dict]:
    """Charge les annotations depuis un fichier JSONL (fallback si DB locale inaccessible)."""
    rows = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print(
        f"  {GREEN}[JSONL]{RESET} {len(rows)} annotation(s) chargees depuis {jsonl_path}."
    )
    return rows


def export_to_jsonl(rows: list[dict], output_path: Path) -> None:
    """Exporte les annotations locales en JSONL pour audit/backup."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            # Serialiser les types non-JSON (datetime, UUID, etc.)
            serializable = {}
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    serializable[k] = v.isoformat()
                elif isinstance(v, uuid.UUID):
                    serializable[k] = str(v)
                else:
                    serializable[k] = v
            f.write(json.dumps(serializable, ensure_ascii=False) + "\n")
    print(f"  {GREEN}[EXPORT]{RESET} JSONL ecrit : {output_path}")


def classify_annotations(rows: list[dict]) -> dict[str, list[dict]]:
    """Classe les annotations par statut de sync."""
    to_sync = []
    to_skip = []

    for row in rows:
        if row.get("is_validated") is True or row.get("is_validated") in (
            "true",
            "1",
            True,
        ):
            to_sync.append(row)
        elif row.get("is_validated") is False or row.get("is_validated") in (
            "false",
            "0",
            False,
            None,
        ):
            to_sync.append(
                row
            )  # sync aussi les non-validees (annotees mais en attente)
        else:
            to_skip.append(row)

    print(f"  Classification : {len(to_sync)} a sync, {len(to_skip)} skippees")
    return {"sync": to_sync, "skip": to_skip}


def get_existing_railway_ids(cur) -> set[str]:
    """Retourne les IDs deja presents sur Railway."""
    cur.execute("SELECT id::text FROM public.annotation_registry")
    return {r["id"] for r in cur.fetchall()}


def import_to_railway(
    rows: list[dict],
    railway_url: str,
    dry_run: bool = True,
) -> dict:
    """Importe les annotations dans Railway en transaction atomique."""
    conn = _connect(railway_url, autocommit=False)

    try:
        with conn.cursor() as cur:
            existing_ids = get_existing_railway_ids(cur)
            print(f"  Railway : {len(existing_ids)} annotation(s) existantes")

            to_insert = []
            already_present = 0
            for row in rows:
                row_id = str(row.get("id", ""))
                if row_id and row_id in existing_ids:
                    already_present += 1
                    continue
                to_insert.append(row)

            print(f"  {len(to_insert)} a inserer, {already_present} deja presentes")

            if dry_run:
                print(f"  {YELLOW}[DRY-RUN]{RESET} Aucune insertion effectuee.")
                conn.rollback()
                conn.close()
                return {
                    "inserted": 0,
                    "already_present": already_present,
                    "to_insert": len(to_insert),
                    "dry_run": True,
                }

            inserted = 0
            errors = 0
            for row in to_insert:
                try:
                    cols = [c for c in ANNOTATION_REGISTRY_COLS if c in row]
                    placeholders = ", ".join(f"%({c})s" for c in cols)
                    col_list = ", ".join(cols)
                    # Normaliser les valeurs
                    normalized = {}
                    for k in cols:
                        v = row.get(k)
                        if isinstance(v, uuid.UUID):
                            normalized[k] = str(v)
                        elif hasattr(v, "isoformat"):
                            normalized[k] = v.isoformat()
                        else:
                            normalized[k] = v
                    cur.execute(
                        f"INSERT INTO public.annotation_registry ({col_list}) "
                        f"VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING",
                        normalized,
                    )
                    inserted += cur.rowcount  # 0 si ON CONFLICT DO NOTHING
                except Exception as exc:
                    errors += 1
                    print(
                        f"  {RED}[ERR]{RESET} Insert {row.get('id')}: {exc}",
                        file=sys.stderr,
                    )

            # Verification post-insert
            cur.execute(
                "SELECT COUNT(*) as cnt FROM public.annotation_registry WHERE is_validated = true"
            )
            validated_count = int(cur.fetchone()["cnt"])

            if errors > 0:
                print(
                    f"  {RED}[ROLLBACK]{RESET} {errors} erreur(s) — rollback automatique."
                )
                conn.rollback()
                conn.close()
                return {"inserted": 0, "errors": errors, "rolled_back": True}

            conn.commit()
            conn.close()

            return {
                "inserted": inserted,
                "already_present": already_present,
                "errors": errors,
                "validated_count_post_sync": validated_count,
                "gate_regle23": validated_count >= GATE_MIN_VALIDATED,
            }

    except Exception as exc:
        print(f"  {RED}[ERR]{RESET} Erreur transaction : {exc}", file=sys.stderr)
        conn.rollback()
        conn.close()
        raise


def print_gate_result(result: dict) -> None:
    validated = result.get("validated_count_post_sync", 0)
    gate_ok = result.get("gate_regle23", False)

    print(f"\n  {BOLD}Gate REGLE-23{RESET}")
    if gate_ok:
        print(
            f"  {GREEN}[VERT]{RESET} annotation_registry.is_validated = {validated} >= {GATE_MIN_VALIDATED}"
        )
    else:
        delta = GATE_MIN_VALIDATED - validated
        print(
            f"  {RED}[ROUGE]{RESET} annotation_registry.is_validated = {validated} < {GATE_MIN_VALIDATED}\n"
            f"  Delta : {delta} annotations manquantes\n"
            f"  Estim. temps : {delta * 45} min (@ 45 min/annotation)\n"
            f"  M15 bloque jusqu'a gate atteint"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync annotations locales → Railway (Phase 2 M15)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Mode simulation (defaut). Aucune ecriture.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Appliquer reellement l'import (desactive dry-run).",
    )
    parser.add_argument(
        "--from-jsonl",
        type=str,
        default=None,
        help="Charger les annotations depuis un fichier JSONL au lieu de la DB locale.",
    )
    parser.add_argument(
        "--export-jsonl",
        type=str,
        default=None,
        help="Exporter les annotations locales en JSONL (backup avant sync).",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    railway_url = _get_railway_url()
    target = (
        railway_url.split("@")[-1].split("/")[0]
        if "@" in railway_url
        else railway_url[:30]
    )

    print(f"\n{BOLD}SYNC ANNOTATIONS LOCAL -> RAILWAY{RESET}")
    print(f"Mode : {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Cible Railway : {target}")
    print()

    # Charger les annotations
    if args.from_jsonl:
        jsonl_path = Path(args.from_jsonl)
        if not jsonl_path.exists():
            print(
                f"{RED}[ERR]{RESET} Fichier JSONL introuvable : {jsonl_path}",
                file=sys.stderr,
            )
            return 1
        rows = fetch_from_jsonl(jsonl_path)
    else:
        local_url = _get_local_url()
        rows = fetch_local_annotations(local_url)
        if not rows:
            print(
                f"\n{YELLOW}[WARN]{RESET} Aucune annotation locale recuperee.\n"
                "  Options :\n"
                "  1. Definir LOCAL_DATABASE_URL avec les bons credentials\n"
                "  2. Utiliser --from-jsonl <fichier.jsonl> si export deja realise\n"
                "  3. Exporter manuellement : pg_dump -t annotation_registry | ... | python import.py\n",
                file=sys.stderr,
            )
            return 2

    # Export JSONL optionnel (backup)
    if args.export_jsonl:
        export_to_jsonl(rows, Path(args.export_jsonl))
    elif not dry_run:
        # Auto-export avant tout apply
        backup_path = (
            ROOT
            / "docs"
            / "data"
            / f"annotations_backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        export_to_jsonl(rows, backup_path)

    # Classifier
    classified = classify_annotations(rows)
    to_sync = classified["sync"]

    if not to_sync:
        print(f"\n{YELLOW}[WARN]{RESET} Aucune annotation a synchroniser.")
        return 0

    # Import Railway
    print(f"\n  Import Railway ({len(to_sync)} annotations)...")
    result = import_to_railway(to_sync, railway_url, dry_run=dry_run)

    # Rapport
    print(f"\n{BOLD}Resultat :{RESET}")
    for k, v in result.items():
        print(f"  {k:35}: {v}")

    if not dry_run:
        print_gate_result(result)

        gate_ok = result.get("gate_regle23", False)
        return 0 if gate_ok else 3  # exit 3 = gate non atteint (bloquant M15)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
