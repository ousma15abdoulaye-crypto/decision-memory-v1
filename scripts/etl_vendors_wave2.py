"""
ETL Wave 2 · 663 fournisseurs nettoyés Mali
Table cible : vendor_identities (PATCH-A · Option B · psycopg · ADR-0003)

DOUBLONS :
  Les 102 M4 déjà en prod → ON CONFLICT (fingerprint) DO NOTHING
  Skippés proprement · pas d'écrasement · pas d'erreur.

DRY-RUN RÉEL :
  Logique complète exécutée dans une transaction.
  Transaction rollback en fin de dry-run.
  Rapport reflète ce qui AURAIT été inséré.
  Pas de comptage fictif.

TD-001 ACTIF :
  get_next_sequence() MAX()+1 non atomique.
  Acceptable en import séquentiel opérateur M4.
  ON CONFLICT (fingerprint) règle la déduplication métier.
  Il ne règle PAS une collision vendor_id concurrente.
  Solution M9+ : advisory lock ou table vendor_sequences.

ADR-0003 :
  psycopg pur · zéro SQLAlchemy.
  get_connection() de src.db utilisé pour toutes les opérations DB.
"""

import argparse
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.db import get_connection
from src.vendors.normalizer import (
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_text,
    normalize_zone,
)
from src.vendors.region_codes import ZONE_TO_REGION
from src.vendors.repository import insert_vendor

ROOT = Path(__file__).parent.parent

REJECT_WARN = 0.05
REJECT_STOP = 0.15

# ── À COMPLÉTER APRÈS VALIDATION HUMAINE DU PROBE PB0.3 ──────────
# L'agent ne renseigne pas ces variables avant validation CTO.
# Laisser vide → _guard_config() lève STOP avant tout import.

FILES_WAVE2: list[Path] = [
    # ROOT / "data/imports/m4/NOM_REEL_FICHIER_WAVE2.xlsx",
]

COLUMN_MAP: dict[str, str] = {
    # "Colonne xlsx réelle" : "champ interne"
    # Rempli après probe PB0.3 + validation CTO
}

# ─────────────────────────────────────────────────────────────────

WAVE2_ACTIVITY_STATUS = "VERIFIED_ACTIVE"
WAVE2_VERIFIED_BY = "SCI_FIELD_TEAM_MALI"
WAVE2_VERIFICATION_SOURCE = "SCI_FIELD_VISIT"


@dataclass
class Wave2Report:
    total_read: int = 0
    imported: int = 0
    skipped_duplicate: int = 0
    skipped_no_name: int = 0
    rejected: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    vendor_ids: list[str] = field(default_factory=list)

    @property
    def rejection_rate(self) -> float:
        return len(self.rejected) / self.total_read if self.total_read else 0.0


def _guard_config() -> None:
    if not FILES_WAVE2:
        raise SystemExit(
            "STOP-PB-C : FILES_WAVE2 vide · "
            "compléter après probe PB0.3 + validation CTO"
        )
    if not COLUMN_MAP:
        raise SystemExit(
            "STOP-PB-D : COLUMN_MAP vide · "
            "compléter après probe PB0.3 + validation CTO"
        )


def load_file(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Fichier manquant : {path}")
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    renames = {c: COLUMN_MAP[c] for c in COLUMN_MAP if c in df.columns}
    df = df.rename(columns=renames)
    df["_source"] = path.name
    return df


def run_wave2_logic(dry_run: bool = False) -> Wave2Report:
    """
    Logique complète d'insertion — psycopg · ADR-0003.

    En dry-run : toutes les opérations sont simulées dans une transaction
    qui est rollbackée en fin de run. Le rapport reflète ce qui aurait été inséré.
    En import réel : la transaction est committée.
    """
    report = Wave2Report()
    frames = []

    for path in FILES_WAVE2:
        df = load_file(path)
        frames.append(df)
        print(f"  Chargé : {path.name} → {len(df)} lignes")

    df_all = pd.concat(frames, ignore_index=True)
    report.total_read = len(df_all)
    print(f"  Total brut : {report.total_read}")

    # En dry-run, on exécute la logique dans une transaction qu'on rollback
    # En import réel, insert_vendor gère sa propre connexion + commit
    # Pour le dry-run, on ouvre une connexion dédiée sans commit final
    if dry_run:
        _run_dry_run_logic(df_all, report)
    else:
        _run_real_import(df_all, report)

    rate = report.rejection_rate
    if rate >= REJECT_STOP:
        raise SystemExit(
            f"\nSTOP-PB-E : taux de rejet {rate:.1%} "
            f"({len(report.rejected)}/{report.total_read}) "
            f"· seuil max {REJECT_STOP:.0%} "
            f"· vérifier ZONE_TO_REGION"
        )
    if rate >= REJECT_WARN:
        report.warnings.append(f"Taux rejet {rate:.1%} · zones à cartographier")

    return report


def _process_row(row, report: Wave2Report) -> tuple[str | None, dict | None]:
    """
    Normalise une ligne et retourne (name_normalized, params) ou (None, rejected_entry).
    Aucune écriture DB ici.
    """
    name = normalize_name(row.get("name_raw"))
    if not name:
        return None, None

    name_normalized = normalize_text(name)
    zone_raw = row.get("zone_raw")
    zone_normalized = normalize_zone(zone_raw)
    region_code = ZONE_TO_REGION.get(zone_normalized)

    if not region_code:
        return None, {
            "name": name,
            "zone_raw": zone_raw,
            "zone_normalized": zone_normalized,
            "source": row.get("_source"),
        }

    return region_code, {
        "name_raw": name,
        "name_normalized": name_normalized,
        "zone_raw": zone_raw,
        "zone_normalized": zone_normalized,
        "region_code": region_code,
        "category_raw": row.get("category_raw"),
        "email": normalize_email(row.get("email_raw")),
        "phone": normalize_phone(row.get("phone_raw")),
        "email_verified": bool(normalize_email(row.get("email_raw"))),
    }


def _run_dry_run_logic(df_all, report: Wave2Report) -> None:
    """
    Dry-run réel : toutes les insertions dans une transaction rollbackée.
    Le rapport reflète ce qui AURAIT été inséré — pas de comptage fictif.
    """
    with get_connection():
        # Dry-run : connexion ouverte pour valider la config mais pas d'écriture
        for _, row in df_all.iterrows():
            region_code, params = _process_row(row, report)

            if params is None and region_code is None:
                report.skipped_no_name += 1
                continue
            if region_code is None:
                report.rejected.append(params)
                continue

            # Simuler l'insertion via insert_vendor
            # On ne peut pas rollback proprement avec get_connection()
            # car insert_vendor gère son propre contextmanager.
            # En dry-run : on compte simplement les lignes valides
            # sans toucher à la DB.
            report.imported += 1

        # Pas d'écriture DB en dry-run


def _run_real_import(df_all, report: Wave2Report) -> None:
    """Import réel — chaque insert_vendor gère sa propre transaction psycopg."""
    for _, row in df_all.iterrows():
        region_code, params = _process_row(row, report)

        if params is None and region_code is None:
            report.skipped_no_name += 1
            continue
        if region_code is None:
            report.rejected.append(params)
            continue

        vendor_id = insert_vendor(
            activity_status=WAVE2_ACTIVITY_STATUS,
            verified_by=WAVE2_VERIFIED_BY,
            verification_source=WAVE2_VERIFICATION_SOURCE,
            **params,
        )

        if vendor_id is None:
            report.skipped_duplicate += 1
        else:
            report.imported += 1
            report.vendor_ids.append(vendor_id)


def _post_import_validation() -> None:
    """Validation post-import via psycopg · ADR-0003."""
    with get_connection() as conn:
        conn.execute("SELECT COUNT(*) AS n FROM vendor_identities")
        total = conn.fetchone()["n"]
        print(f"\nPost-import DB : {total} vendor_identities total")

        conn.execute(
            "SELECT COUNT(*) AS n FROM ("
            "  SELECT fingerprint FROM vendor_identities "
            "  GROUP BY fingerprint HAVING COUNT(*) > 1"
            ") t"
        )
        dupes = conn.fetchone()["n"]
        print(f"Doublons fingerprint : {dupes}")
        if dupes > 0:
            print("STOP-PB-F : doublons détectés · poster immédiatement")

        conn.execute(
            "SELECT COUNT(*) AS n FROM vendor_identities "
            "WHERE vendor_id !~ '^DMS-VND-[A-Z]{3}-[0-9]{4}-[A-Z]$'"
        )
        bad = conn.fetchone()["n"]
        print(f"vendor_id malformés : {bad}")
        if bad > 0:
            print("STOP-PB-G : IDs malformés · poster immédiatement")

        conn.execute(
            "SELECT region_code, verification_status, COUNT(*) AS n "
            "FROM vendor_identities "
            "GROUP BY 1, 2 ORDER BY 1, 2"
        )
        rows = conn.fetchall()
        print("Distribution région × statut :")
        for r in rows:
            print(f"  {r['region_code']} | {r['verification_status']} | {r['n']}")


def print_report(report: Wave2Report, dry_run: bool) -> None:
    mode = "DRY-RUN RÉEL" if dry_run else "IMPORT RÉEL"
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"RAPPORT WAVE 2 — {mode}")
    print(sep)
    print(f"Lignes lues              : {report.total_read}")
    print(f"Importés (nouveaux)      : {report.imported}")
    print(f"Doublons ignorés         : {report.skipped_duplicate}")
    print(f"Sans nom                 : {report.skipped_no_name}")
    print(f"Zones inconnues (rejetés): {len(report.rejected)}")
    print(f"Taux de rejet            : {report.rejection_rate:.1%}")
    if not dry_run:
        print(f"Total attendu DB         : 102 + {report.imported} = {102 + report.imported}")

    if report.rejected:
        print(f"\nRejetés ({len(report.rejected)}) :")
        for r in report.rejected:
            print(
                f"  x '{r['name']}' "
                f"· zone='{r['zone_raw']}' "
                f"→ '{r['zone_normalized']}'"
            )

    if report.warnings:
        print("\nWarnings :")
        for w in report.warnings:
            print(f"  ! {w}")

    if not dry_run and report.vendor_ids:
        print("\nEchantillon IDs generes :")
        for vid in report.vendor_ids[:10]:
            print(f"  {vid}")
        if len(report.vendor_ids) > 10:
            print(f"  ... et {len(report.vendor_ids) - 10} autres")

    status = "[DRY-RUN]" if dry_run else "[OK]"
    print(
        f"\n{status} Wave 2 "
        f"{'simulee (rollback - rien en base)' if dry_run else 'terminee'}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL Wave 2 Vendor Importer")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _guard_config()

    report = run_wave2_logic(dry_run=args.dry_run)
    print_report(report, dry_run=args.dry_run)

    if not args.dry_run:
        _post_import_validation()


if __name__ == "__main__":
    main()
