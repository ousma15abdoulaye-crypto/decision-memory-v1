"""
scripts/import_mercuriale.py

Import mercuriales PDF → DMS DB · Phase 1 (2024 d'abord · 2023 ensuite)

Ordre d'import :
  2024 d'abord : 1 fichier combiné · structure bloc par zone · calibre le parser
  2023 ensuite : 16 fichiers · 1 par zone · zone extraite du nom de fichier

Usage :
  python scripts/import_mercuriale.py --dry-run
  python scripts/import_mercuriale.py

Clé API : variable LLAMADMS dans l'environnement local ou Railway Dashboard
Ne jamais hardcoder la clé.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
)
logger = logging.getLogger(__name__)

# ── Mapping nom fichier → zone_raw canonical ─────────────────────────────────
_ZONE_FROM_FILENAME: dict[str, str] = {
    "bko": "Bamako",
    "bamako": "Bamako",
    "bougouni": "Bougouni",
    "dioila": "Dioïla",
    "gao": "Gao",
    "kidal": "Kidal",
    "kita": "Kita",
    "koulikoro": "Koulikoro",
    "menaka": "Ménaka",
    "mopti": "Mopti",
    "nara": "Nara",
    "nioro": "Nioro",
    "san": "San",
    "segou": "Ségou",
    "sikasso": "Sikasso",
    "taoudeni": "Taoudeni",
    "tombouctou": "Tombouctou",
}


def _zone_from_filename(filename: str) -> str | None:
    """Extrait zone_raw depuis nom de fichier ex: Bulletin_Result_Mopti2023.pdf."""
    name = Path(filename).stem.lower()
    name = re.sub(r"[^a-zàâäéèêëîïôùûüç]", "", name)
    for key, zone in _ZONE_FROM_FILENAME.items():
        if key in name:
            return zone
    return None


def build_files_2023(folder: Path) -> list[dict]:
    """Construit la liste des fichiers 2023 avec leur zone depuis le nom de fichier."""
    files = []
    if not folder.exists():
        logger.warning("Dossier 2023 introuvable : %s", folder)
        return files

    for pdf in sorted(folder.glob("*.pdf")):
        zone = _zone_from_filename(pdf.name)
        if zone is None:
            logger.warning("Zone non détectée depuis nom fichier : %s", pdf.name)
        files.append(
            {
                "path": pdf,
                "year": 2023,
                "source_type": "official_dgmp",
                "default_zone_raw": zone,
            }
        )
    return files


# 2024 d'abord : 1 fichier combiné
_PDF_2024 = Path(
    "data/imports/m5/Mercuriale des prix 2024 ( Combiné de Toutes les regions ).pdf"
)

# 2023 ensuite : 16 fichiers dans le sous-dossier
_FOLDER_2023 = Path("data/imports/m5/Mercuriale des prix 2023")

FILES_PHASE1 = [
    {
        "path": _PDF_2024,
        "year": 2024,
        "source_type": "official_dgmp",
        "default_zone_raw": None,
    },
] + build_files_2023(_FOLDER_2023)


def _guard() -> None:
    import os

    if not (
        os.environ.get("LLAMADMS", "").strip()
        or os.environ.get("LLAMA_CLOUD_API_KEY", "").strip()
    ):
        logger.error(
            "Clé API absente (LLAMADMS ou LLAMA_CLOUD_API_KEY). "
            "Exporter localement : $env:LLAMADMS='llx-...' "
            "ou vérifier Railway Dashboard."
        )
        sys.exit(1)

    missing = [e["path"] for e in FILES_PHASE1 if not e["path"].exists()]
    if missing:
        for p in missing:
            logger.error("PDF introuvable : %s", p)
        logger.error("Déposer les PDFs dans data/imports/m5/ puis relancer.")
        sys.exit(1)


def _print_report(r: object, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "RÉEL"
    print(f"\n{'='*60}")
    print(f"  {r.filename} ({r.year}) · Mode {mode}")
    print(f"{'='*60}")

    if r.already_imported:
        print("  Déjà importé (SHA256 connu) · skip")
        return

    print(f"  Total parsé          : {r.total_rows_parsed}")
    print(f"  Insérées             : {r.inserted}")
    print(f"  Review requis        : {r.review_required}")
    print(f"  Skipped vide         : {r.skipped_empty}")
    print(f"  Skipped prix invalid : {r.skipped_price_invalid}")
    print(f"  Skipped confidence   : {r.skipped_low_confidence}")
    print(f"  Zones résolues       : {r.zones_resolved}")
    print(f"  Zones non résolues   : {r.zones_unresolved}")
    print(f"  Coverage             : {r.coverage_pct}%")

    if r.errors:
        print(f"\n  Erreurs ({len(r.errors)}) :")
        for e in r.errors[:5]:
            print(f"     - {e}")
        if len(r.errors) > 5:
            print(f"     ... et {len(r.errors) - 5} autres")


def main(dry_run: bool = False) -> None:
    from src.couche_b.mercuriale.importer import import_mercuriale

    _guard()

    print(f"\n{'='*60}")
    print("  DMS — Mercuriale Ingest · Phase 1")
    print(f"  Mode      : {'DRY-RUN' if dry_run else 'IMPORT RÉEL'}")
    print(f"  Fichiers  : {len(FILES_PHASE1)}")
    print("  Ordre     : 2024 (simple) → 2023 (dense · 16 zones)")
    print(f"{'='*60}\n")

    total_inserted = 0
    total_review = 0
    total_unresolved = 0

    for entry in FILES_PHASE1:
        logger.info("Traitement : %s", entry["path"].name)
        try:
            r = import_mercuriale(
                filepath=entry["path"],
                year=entry["year"],
                source_type=entry["source_type"],
                default_zone_raw=entry.get("default_zone_raw"),
                dry_run=dry_run,
            )
            _print_report(r, dry_run)
            total_inserted += r.inserted
            total_review += r.review_required
            total_unresolved += r.zones_unresolved
        except Exception as e:
            logger.error("ÉCHEC %s : %s", entry["path"].name, e)

    print(f"\n{'='*60}")
    print("  RÉSUMÉ PHASE 1")
    print(f"{'='*60}")
    print(f"  Total insérées       : {total_inserted}")
    print(f"  Total review requis  : {total_review}")
    print(f"  Zones non résolues   : {total_unresolved}")
    print(f"  Mode                 : {'DRY-RUN' if dry_run else 'RÉEL'}")

    if dry_run:
        print("\n  Dry-run terminé.")
        print("  Poster ce rapport au CTO · attendre GO avant import réel.")
    elif total_inserted == 0:
        logger.warning("Zéro ligne insérée · vérifier logs parser")
    else:
        print(f"\n  {total_inserted} articles mercuriels en base.")
        print("  Poster ce rapport au CTO avant de merger.")

    print()


if __name__ == "__main__":
    _dry = "--dry-run" in sys.argv
    _year: int | None = None
    for _arg in sys.argv[1:]:
        if _arg.startswith("--year="):
            _year = int(_arg.split("=")[1])
        elif _arg.lstrip("-").isdigit():
            _year = int(_arg.lstrip("-"))

    if _year is not None:
        FILES_PHASE1[:] = [e for e in FILES_PHASE1 if e["year"] == _year]
        if not FILES_PHASE1:
            logger.error("Aucun fichier pour l'année %s", _year)
            sys.exit(1)
        logger.info("Mode année %s · %d fichier(s)", _year, len(FILES_PHASE1))

    main(dry_run=_dry)
