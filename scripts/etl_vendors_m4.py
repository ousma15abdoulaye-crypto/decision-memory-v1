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

Schéma cible (migration 043 + m4_patch_a + m5_pre_vendors_consolidation) :
  Table : vendors (renommée depuis vendor_identities via m5_pre_vendors_consolidation)
  Colonnes obligatoires :
    vendor_id, fingerprint, name_raw, name_normalized, canonical_name,
    region_code, activity_status, email_verified, is_active
  Valeurs activity_status valides :
    VERIFIED_ACTIVE | UNVERIFIED | INACTIVE | GHOST_SUSPECTED

Vérification pré-import :
  run_preflight_checks() valide le schéma DB avant tout INSERT.
  En cas de mismatch, l'import est bloqué avec un message explicite.
  Utiliser --skip-preflight uniquement si la DB est inaccessible en CI.

Compatibilité migrations 078/079 :
  Après déploiement de 078/079, relancer --check-migration-compat
  pour vérifier que le schéma vendors est toujours compatible.
  Voir scripts/README_VENDOR_IMPORT.md pour la procédure complète.
"""

import argparse
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# Force UTF-8 sur Windows (PowerShell cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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

# ── Schéma attendu (post-migration 043 + m4_patch_a + m5_pre_vendors_consolidation) ──
# Ces constantes sont la source de vérité pour les pré-vérifications.
# Si le schéma change (migrations 078/079), mettre à jour ici ET dans
# scripts/README_VENDOR_IMPORT.md.
REQUIRED_TABLE = "vendors"

REQUIRED_COLUMNS: set[str] = {
    "vendor_id",
    "fingerprint",
    "name_raw",
    "name_normalized",
    "canonical_name",
    "zone_raw",
    "zone_normalized",
    "region_code",
    "category_raw",
    "email",
    "phone",
    "email_verified",
    "activity_status",
    "verified_by",
    "verification_source",
    "is_active",
    "source",
    "created_at",
    "updated_at",
}

VALID_ACTIVITY_STATUSES: set[str] = {
    "VERIFIED_ACTIVE",
    "UNVERIFIED",
    "INACTIVE",
    "GHOST_SUSPECTED",
}

# Colonnes NOT NULL sans DEFAULT — doivent être fournies explicitement à chaque INSERT
NOT_NULL_COLUMNS: set[str] = {
    "vendor_id",
    "fingerprint",
    "name_raw",
    "name_normalized",
    "canonical_name",
    "region_code",
    "email_verified",
    "activity_status",
    "is_active",
    "source",
}


def run_preflight_checks() -> None:
    """
    Vérifie que le schéma DB est compatible avec cet ETL avant tout INSERT.

    Contrôles effectués :
      1. Table vendors existe (post-m5_pre_vendors_consolidation)
      2. Toutes les colonnes requises sont présentes
      3. La contrainte CHECK sur activity_status accepte les valeurs attendues
      4. Aucune colonne NOT NULL obligatoire n'est manquante

    Raises :
      SystemExit : si un contrôle échoue — message explicite avec la correction
                   à apporter (migration manquante, colonne absente, etc.)

    Note :
      Cette fonction utilise get_connection() (ADR-0003 · psycopg pur).
      Elle doit être appelée AVANT run_etl() pour bloquer l'import en cas
      de mismatch schéma — évite les 661 erreurs silencieuses de type
      "null value in column vendor_id" ou "invalid activity_status value".
    """
    from src.db import get_connection  # noqa: PLC0415 — import local intentionnel

    print("Pré-vérification schéma DB...")

    with get_connection() as conn:
        # ── Contrôle 1 : table vendors existe ────────────────────────────────
        conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name   = %(table)s
            """,
            {"table": REQUIRED_TABLE},
        )
        row = conn.fetchone()
        if not row or row["n"] == 0:
            raise SystemExit(
                f"\nSTOP-PREFLIGHT-1 : table '{REQUIRED_TABLE}' introuvable.\n"
                "  Cause probable : migration m5_pre_vendors_consolidation non appliquée,\n"
                "  ou la table s'appelle encore 'vendor_identities'.\n"
                "  Correction : alembic upgrade head\n"
                "  Puis relancer : python scripts/etl_vendors_m4.py --dry-run"
            )

        # ── Contrôle 2 : colonnes requises présentes ──────────────────────────
        conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = %(table)s
            """,
            {"table": REQUIRED_TABLE},
        )
        existing_columns = {r["column_name"] for r in conn.fetchall()}
        missing = REQUIRED_COLUMNS - existing_columns
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise SystemExit(
                f"\nSTOP-PREFLIGHT-2 : colonnes manquantes dans '{REQUIRED_TABLE}' : "
                f"{missing_list}\n"
                "  Cause probable : migrations 041-043 ou m4_patch_a_vendor_structure_v410\n"
                "  non appliquées, ou schéma sur une ancienne branche.\n"
                "  Colonnes manquantes typiques :\n"
                "    vendor_id / region_code / canonical_name → migration 041 ou m4_patch_a\n"
                "    activity_status / verified_by / verification_source → migration 043\n"
                "  Correction : alembic upgrade head\n"
                "  Puis relancer : python scripts/etl_vendors_m4.py --dry-run"
            )

        # ── Contrôle 3 : contrainte CHECK activity_status valide ─────────────
        conn.execute(
            """
            SELECT pg_get_constraintdef(c.oid) AS def
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname  = %(table)s
              AND c.conname  = 'chk_activity_status'
              AND c.contype  = 'c'
            """,
            {"table": REQUIRED_TABLE},
        )
        row = conn.fetchone()
        if row is None:
            raise SystemExit(
                f"\nSTOP-PREFLIGHT-3 : contrainte 'chk_activity_status' absente "
                f"sur '{REQUIRED_TABLE}'.\n"
                "  Cause probable : migration 043_vendor_activity_badge non appliquée.\n"
                "  Correction : alembic upgrade head\n"
                "  Puis relancer : python scripts/etl_vendors_m4.py --dry-run"
            )
        constraint_def = row["def"]
        for status in VALID_ACTIVITY_STATUSES:
            if status not in constraint_def:
                raise SystemExit(
                    f"\nSTOP-PREFLIGHT-3 : valeur '{status}' absente de la contrainte "
                    f"chk_activity_status.\n"
                    f"  Contrainte actuelle : {constraint_def}\n"
                    "  Valeurs attendues : "
                    + ", ".join(sorted(VALID_ACTIVITY_STATUSES))
                    + "\n"
                    "  Cause probable : migration 043 appliquée avec une version différente\n"
                    "  ou contrainte modifiée manuellement.\n"
                    "  Correction : vérifier alembic/versions/043_vendor_activity_badge.py"
                )

        # ── Contrôle 4 : colonnes NOT NULL sans DEFAULT présentes ─────────────
        conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema    = 'public'
              AND table_name      = %(table)s
              AND is_nullable     = 'NO'
              AND column_default  IS NULL
            """,
            {"table": REQUIRED_TABLE},
        )
        db_not_null_no_default = {r["column_name"] for r in conn.fetchall()}
        # Vérifie que nos colonnes NOT NULL obligatoires sont bien dans la DB
        unexpected_missing = NOT_NULL_COLUMNS - existing_columns
        if unexpected_missing:
            raise SystemExit(
                f"\nSTOP-PREFLIGHT-4 : colonnes NOT NULL obligatoires manquantes : "
                f"{', '.join(sorted(unexpected_missing))}\n"
                "  Ces colonnes doivent être fournies à chaque INSERT.\n"
                "  Correction : alembic upgrade head"
            )

    print(
        f"  [OK] Table '{REQUIRED_TABLE}' présente · "
        f"{len(existing_columns)} colonnes · "
        f"contrainte activity_status valide."
    )


@dataclass
class ETLReport:
    total_read: int = 0
    imported: int = 0
    skipped_duplicate: int = 0
    skipped_no_name: int = 0
    # skipped_no_region supprimé (Patch M4) — cas sans région → rejected[]
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
                # Lots SCI verifies terrain → VERIFIED_ACTIVE
                activity_status="VERIFIED_ACTIVE",
                verified_by="SCI_FIELD_TEAM_MALI",
                verification_source="SCI_FIELD_VISIT",
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
    print(f"Zones inconnues (rej): {len(report.rejected)}")
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


def check_migration_compat() -> None:
    """
    Vérifie la compatibilité du schéma vendors après déploiement de nouvelles migrations.

    À utiliser après le déploiement de migrations 078/079 (ou toute migration future
    touchant la table vendors) pour confirmer que l'ETL reste opérationnel.

    Contrôles effectués :
      - Tous les contrôles de run_preflight_checks()
      - Colonnes ajoutées par 078/079 qui pourraient casser les INSERTs existants
        (ex. nouvelle colonne NOT NULL sans DEFAULT)
      - Contraintes CHECK modifiées sur activity_status

    Usage :
        python scripts/etl_vendors_m4.py --check-migration-compat

    Sortie :
      [OK]  → schéma compatible · ETL peut tourner sans modification
      [WARN] → colonnes nouvelles détectées · vérifier si INSERT doit être mis à jour
      [STOP] → incompatibilité bloquante · mettre à jour REQUIRED_COLUMNS et repository.py
    """
    from src.db import get_connection  # noqa: PLC0415

    sep = "=" * 60
    print(f"\n{sep}")
    print("VÉRIFICATION COMPATIBILITÉ MIGRATIONS — vendors")
    print(sep)

    # Réutilise les contrôles de base
    run_preflight_checks()

    with get_connection() as conn:
        # ── Colonnes actuelles en DB ──────────────────────────────────────────
        conn.execute(
            """
            SELECT column_name, is_nullable, column_default, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = %(table)s
            ORDER BY ordinal_position
            """,
            {"table": REQUIRED_TABLE},
        )
        db_columns = {r["column_name"]: r for r in conn.fetchall()}

        # ── Colonnes inconnues de cet ETL ─────────────────────────────────────
        unknown_columns = set(db_columns.keys()) - REQUIRED_COLUMNS
        if unknown_columns:
            print(
                f"\n  [WARN] Colonnes présentes en DB mais inconnues de cet ETL : "
                f"{', '.join(sorted(unknown_columns))}"
            )
            # Vérifie si l'une d'elles est NOT NULL sans DEFAULT → INSERT cassé
            blocking = []
            for col in unknown_columns:
                info = db_columns[col]
                if info["is_nullable"] == "NO" and info["column_default"] is None:
                    blocking.append(col)
            if blocking:
                raise SystemExit(
                    f"\n  STOP-COMPAT-1 : nouvelles colonnes NOT NULL sans DEFAULT "
                    f"détectées : {', '.join(sorted(blocking))}\n"
                    "  Ces colonnes casseront les INSERTs existants.\n"
                    "  Actions requises :\n"
                    "    1. Ajouter ces colonnes à REQUIRED_COLUMNS dans etl_vendors_m4.py\n"
                    "    2. Mettre à jour insert_vendor() dans src/vendors/repository.py\n"
                    "    3. Relancer --dry-run pour valider\n"
                    "  Voir scripts/README_VENDOR_IMPORT.md §Migrations 078/079"
                )
            else:
                print(
                    "    → Toutes nullable ou avec DEFAULT · INSERT existant non cassé."
                )
        else:
            print("  [OK] Aucune colonne inconnue · schéma stable.")

        # ── Contrainte activity_status inchangée ──────────────────────────────
        conn.execute(
            """
            SELECT pg_get_constraintdef(c.oid) AS def
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = %(table)s
              AND c.conname = 'chk_activity_status'
              AND c.contype = 'c'
            """,
            {"table": REQUIRED_TABLE},
        )
        row = conn.fetchone()
        if row:
            print(f"  [OK] Contrainte chk_activity_status : {row['def']}")
        else:
            print(
                "  [WARN] Contrainte chk_activity_status absente — "
                "peut avoir été renommée ou supprimée par 078/079."
            )

        # ── Résumé ────────────────────────────────────────────────────────────
        conn.execute(f"SELECT COUNT(*) AS n FROM {REQUIRED_TABLE}")  # noqa: S608
        total = conn.fetchone()["n"]
        print(f"\n  Vendors en DB : {total}")

    print(f"\n  [OK] Compatibilité vérifiée · ETL M4 opérationnel.")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL M4 Vendor Importer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help=(
            "Ignorer les vérifications pré-import (CI sans DB). "
            "NE PAS utiliser en production."
        ),
    )
    parser.add_argument(
        "--check-migration-compat",
        action="store_true",
        help=(
            "Vérifier la compatibilité du schéma après déploiement de nouvelles "
            "migrations (ex. 078/079). Ne lance pas l'import."
        ),
    )
    args = parser.parse_args()

    if args.check_migration_compat:
        check_migration_compat()
        return

    if not args.skip_preflight:
        run_preflight_checks()
    else:
        print(
            "  [WARN] --skip-preflight actif · vérifications schéma ignorées. "
            "NE PAS utiliser en production."
        )

    report = run_etl(dry_run=args.dry_run)
    print_report(report, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
