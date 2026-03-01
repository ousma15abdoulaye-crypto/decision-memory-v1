"""
ETL M4 — Vendor Importer Mali

Lit les xlsx → normalise → dédup → insère via repository

Usage :
    python scripts/etl_vendors_m4.py           # import réel
    python scripts/etl_vendors_m4.py --dry-run # rapport sans écriture DB

Règles fondamentales :
- vendor_id généré dans repository.insert_vendor() · jamais ici
- toutes les régions reconnues sont importées · pas de filtre régional
- les rejetés sont tracés · taux surveillé · seuils configurés
- le volume final est rapporté tel quel · pas de cible artificielle
- structure Bamako : header à la ligne 2 (2 lignes méta en tête)
"""

import argparse
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# Force UTF-8 sur Windows (PowerShell cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

# Assure que src/ est dans le path quand lancé depuis la racine
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.vendors.normalizer import (  # noqa: E402
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_text,
    normalize_zone,
)
from src.vendors.region_codes import ZONE_TO_REGION  # noqa: E402
from src.vendors.repository import insert_vendor  # noqa: E402

FILES: list[dict] = [
    {
        "path": ROOT / "data/imports/m4/Supplier DATA BAMAKO.xlsx",
        "header": 2,  # 2 lignes méta avant les vrais en-têtes
    },
    {
        "path": ROOT / "data/imports/m4/Supplier DATA Mopti et autres zones nords.xlsx",
        "header": 0,
    },
]

# Seuils de rejet — configurables
REJECT_WARN = 0.05  # 5%  → warning · import continue
REJECT_STOP = 0.15  # 15% → STOP-M4-G · problème systémique

# Mapping colonnes xlsx → champs internes
# Validé après probe B0.3 (2026-03-01)
COLUMN_MAP: dict[str, str] = {
    "Supplier Name": "name_raw",
    "Supplier Email Address": "email_raw",
    "Supplier Phone Number": "phone_raw",
    "Supplier Zone": "zone_raw",
    "Catégorie de Marché": "category_raw",
}


@dataclass
class ETLReport:
    total_read: int = 0
    imported: int = 0
    skipped_duplicate: int = 0
    skipped_no_name: int = 0
    skipped_no_region: int = 0
    rejected: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    vendor_ids: list[str] = field(default_factory=list)

    @property
    def rejection_rate(self) -> float:
        return len(self.rejected) / self.total_read if self.total_read else 0.0


def load_file(file_spec: dict) -> pd.DataFrame:
    path: Path = file_spec["path"]
    header: int = file_spec["header"]
    if not path.exists():
        raise FileNotFoundError(f"Fichier manquant : {path}")
    df = pd.read_excel(path, header=header, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    renames = {c: COLUMN_MAP[c] for c in COLUMN_MAP if c in df.columns}
    df = df.rename(columns=renames)
    df["_source"] = path.name
    return df


def run_etl(dry_run: bool = False) -> ETLReport:
    report = ETLReport()
    frames = []
    for spec in FILES:
        df = load_file(spec)
        frames.append(df)
        print(f"  Charge : {spec['path'].name} -> {len(df)} lignes")

    df_all = pd.concat(frames, ignore_index=True)
    report.total_read = len(df_all)

    for _, row in df_all.iterrows():
        # Nom
        name = normalize_name(row.get("name_raw"))
        if not name:
            report.skipped_no_name += 1
            continue
        name_normalized = normalize_text(name)

        # Zone → région
        zone_raw = row.get("zone_raw")
        zone_normalized = normalize_zone(zone_raw)
        region_code = ZONE_TO_REGION.get(zone_normalized)
        if not region_code:
            report.rejected.append(
                {
                    "name": name,
                    "zone_raw": zone_raw,
                    "zone_normalized": zone_normalized,
                    "_source": row.get("_source"),
                }
            )
            continue

        # Contacts
        email = normalize_email(row.get("email_raw"))
        phone = normalize_phone(row.get("phone_raw"))
        category = row.get("category_raw")

        if not dry_run:
            vendor_id = insert_vendor(
                name_raw=name,
                name_normalized=name_normalized,
                zone_raw=zone_raw,
                zone_normalized=zone_normalized,
                region_code=region_code,
                category_raw=category,
                email=email,
                phone=phone,
                email_verified=bool(email),
            )
            if vendor_id is None:
                report.skipped_duplicate += 1
            else:
                report.imported += 1
                report.vendor_ids.append(vendor_id)
        else:
            report.imported += 1

    # Contrôle seuil de rejet
    rate = report.rejection_rate
    if rate >= REJECT_STOP:
        raise SystemExit(
            f"\nSTOP-M4-G : taux de rejet {rate:.1%} "
            f"({len(report.rejected)}/{report.total_read}) "
            f"· seuil max = {REJECT_STOP:.0%} "
            f"· vérifier ZONE_TO_REGION et les données source"
        )
    elif rate >= REJECT_WARN:
        report.warnings.append(
            f"Taux de rejet {rate:.1%} · vérifier vendors_rejected ci-dessus"
        )

    return report


def print_report(report: ETLReport, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "IMPORT REEL"
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"RAPPORT ETL M4 — {mode}")
    print(sep)
    print(f"Lignes lues          : {report.total_read}")
    print(f"Importés             : {report.imported}")
    print(f"Doublons détectés    : {report.skipped_duplicate}")
    print(f"Sans nom             : {report.skipped_no_name}")
    print(f"Zones inconnues      : {len(report.rejected)}")
    print(f"Taux de rejet        : {report.rejection_rate:.1%}")

    if report.rejected:
        print(f"\nRejetés ({len(report.rejected)}) :")
        for r in report.rejected:
            print(
                f"  x '{r['name']}' "
                f"· zone='{r['zone_raw']}' "
                f"-> normalisé='{r['zone_normalized']}' "
                f"[{r['_source']}]"
            )

    if report.warnings:
        print(f"\nWarnings ({len(report.warnings)}) :")
        for w in report.warnings:
            print(f"  ! {w}")

    if report.vendor_ids and not dry_run:
        sample = report.vendor_ids[:10]
        print(f"\nEchantillon IDs ({len(sample)}) :")
        for vid in sample:
            print(f"  {vid}")
        if len(report.vendor_ids) > 10:
            print(f"  ... et {len(report.vendor_ids) - 10} autres")

    status = "DRY-RUN OK" if dry_run else "ETL M4 termine."
    print(f"\n{status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL M4 Vendor Importer")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_etl(dry_run=args.dry_run)
    print_report(report, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
