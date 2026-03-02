"""
ETL Wave 2 · 663 fournisseurs nettoyés Mali.
Table cible : vendor_identities (34 colonnes · post-PATCH-A).

CORRECTIONS COPILOT (F4-F6) :
  F4 · dry-run réel : run_wave2_logic() unique pour dry-run et import.
       dry_run=True → normalisation + détection doublons par fingerprint SELECT.
       Aucune insertion. Rapport honnête basé sur l'état réel de la DB.
       Suppression _run_dry_run_logic() (logique séparée · rapport menteur).

  F5 · Suppression with get_connection(): parasite.
       psycopg ADR-0003 · une connexion par opération · zéro connexion orpheline.
       insert_vendor() gère sa propre connexion via get_connection().

  F6 · Docstring _process_row corrigée.
       Retourne (region_code, params) · pas (name_normalized, params).

  F7 · Commentaire pg_trgm corrigé.
       pg_trgm déjà activée via 005_add_couche_b.
       Hors scope ici = index GIN + match_vendor_by_name() · pas l'extension.

ADR-0003 :
  psycopg pur · zéro SQLAlchemy.
  insert_vendor() de repository.py gère ses propres connexions psycopg.
  Pas de Session SQLAlchemy transmise en paramètre.

TD-001 ACTIF :
  get_next_sequence() MAX()+1 non atomique.
  Import séquentiel opérateur · 1 processus · risque acceptable M4.
  ON CONFLICT (fingerprint) = déduplication métier.
  Ne résout PAS une collision vendor_id concurrente.
  Solution M9+ : advisory lock ou table vendor_sequences SELECT FOR UPDATE.
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
from src.vendors.repository import generate_fingerprint, insert_vendor

ROOT = Path(__file__).parent.parent

REJECT_WARN = 0.05
REJECT_STOP = 0.15

# ── À COMPLÉTER APRÈS PROBE PB0.3 + VALIDATION CTO ──────────────
# _guard_config() bloque tout lancement si ces variables sont vides.

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
    """
    Bloque tout lancement sans configuration validée CTO.
    Vérifie FILES_WAVE2 · COLUMN_MAP · existence physique des fichiers.
    """
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
    for path in FILES_WAVE2:
        if not path.exists():
            raise SystemExit(f"STOP-PB-J : fichier introuvable → {path}")


def load_file(path: Path) -> pd.DataFrame:
    """Charge xlsx · strip colonnes · applique COLUMN_MAP · ajoute _source."""
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    renames = {c: COLUMN_MAP[c] for c in COLUMN_MAP if c in df.columns}
    df = df.rename(columns=renames)
    df["_source"] = path.name
    return df


def _process_row(row: pd.Series) -> tuple | None:
    """
    Normalise une ligne Excel · prépare les paramètres d'insertion.

    Retourne :
      None                      → nom absent · ligne ignorée
      ("REJECTED", reject_dict) → zone inconnue · ligne rejetée tracée
      (region_code, params)     → ligne valide · prête pour insert_vendor()

    CORRECTION F6 :
      Retourne (region_code, params) · region_code = discriminant de routage.
      Le code appelant distingue REJECTED de valide par ce discriminant.
    """
    name = normalize_name(row.get("name_raw"))
    if not name:
        return None

    name_normalized = normalize_text(name)
    zone_raw = row.get("zone_raw")
    zone_normalized = normalize_zone(zone_raw)
    region_code = ZONE_TO_REGION.get(zone_normalized)

    if not region_code:
        return ("REJECTED", {
            "name": name,
            "zone_raw": zone_raw,
            "zone_normalized": zone_normalized,
            "source": row.get("_source"),
        })

    params = {
        "name_raw": name,
        "name_normalized": name_normalized,
        "zone_raw": zone_raw,
        "zone_normalized": zone_normalized,
        "region_code": region_code,
        "category_raw": row.get("category_raw"),
        "email": normalize_email(row.get("email_raw")),
        "phone": normalize_phone(row.get("phone_raw")),
        "email_verified": bool(normalize_email(row.get("email_raw"))),
        "activity_status": WAVE2_ACTIVITY_STATUS,
        "verified_by": WAVE2_VERIFIED_BY,
        "verification_source": WAVE2_VERIFICATION_SOURCE,
    }
    return (region_code, params)


def run_wave2_logic(dry_run: bool = False) -> Wave2Report:
    """
    Logique complète — fonction unique pour dry-run et import réel.

    CORRECTION F4 + F5 (ADR-0003 · psycopg) :
      La seule différence dry-run/import est dans cette fonction.

      dry-run  → normalisation complète + détection doublons réels par fingerprint.
                 Une seule connexion ouverte avant la boucle pour pré-charger tous
                 les fingerprints existants (zéro INSERT · vérification en mémoire
                 O(1) · rapport honnête sur état DB actuel).

      import   → insert_vendor(**params) via psycopg · ON CONFLICT DO NOTHING.
                 Chaque insert gère sa propre connexion psycopg (ADR-0003).

      Pas de connexion parasite (F5 corrigé).
      Pas de logique séparée _run_dry_run_logic() (F4 corrigé).
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

    # Pré-chargement des fingerprints existants en une seule requête (dry-run uniquement).
    # Évite N connexions DB dans la boucle — une connexion · un SELECT · lookup O(1).
    existing_fingerprints: set[str] = set()
    if dry_run:
        with get_connection() as conn:
            conn.execute("SELECT fingerprint FROM vendor_identities")
            existing_fingerprints = {row["fingerprint"] for row in conn.fetchall()}

    for _, row in df_all.iterrows():
        result = _process_row(row)

        if result is None:
            report.skipped_no_name += 1
            continue

        discriminant, payload = result

        if discriminant == "REJECTED":
            report.rejected.append(payload)
            continue

        region_code = discriminant

        if dry_run:
            # Dry-run réel : détection doublons par fingerprint en mémoire
            # Aucune écriture DB · rapport basé sur l'état réel
            fp = generate_fingerprint(payload["name_normalized"], region_code)
            if fp in existing_fingerprints:
                report.skipped_duplicate += 1
            else:
                report.imported += 1
        else:
            # Import réel — TD-001 : MAX()+1 non atomique · acceptable séquentiel
            vendor_id = insert_vendor(**payload)
            if vendor_id is None:
                report.skipped_duplicate += 1
            else:
                report.imported += 1
                report.vendor_ids.append(vendor_id)

    rate = report.rejection_rate
    if rate >= REJECT_STOP:
        raise SystemExit(
            f"\nSTOP-PB-E : taux rejet {rate:.1%} "
            f"({len(report.rejected)}/{report.total_read}) "
            f"· seuil {REJECT_STOP:.0%} · vérifier ZONE_TO_REGION"
        )
    if rate >= REJECT_WARN:
        report.warnings.append(f"Taux rejet {rate:.1%} · zones à cartographier")

    return report


def _post_import_validation() -> bool:
    """
    Validation post-import sur vendor_identities via psycopg (ADR-0003).
    Retourne True si propre · False si anomalie.
    """
    clean = True
    with get_connection() as conn:

        conn.execute("SELECT COUNT(*) AS n FROM vendor_identities")
        total = conn.fetchone()["n"]
        print(f"\nPost-import vendor_identities : {total} vendors")

        conn.execute(
            "SELECT COUNT(*) AS n FROM ("
            "  SELECT fingerprint FROM vendor_identities "
            "  GROUP BY fingerprint HAVING COUNT(*) > 1"
            ") t"
        )
        dupes_fp = conn.fetchone()["n"]
        print(f"Doublons fingerprint : {dupes_fp}")
        if dupes_fp > 0:
            print("  STOP-PB-F : doublons fingerprint · poster immédiatement")
            clean = False

        conn.execute(
            "SELECT COUNT(*) AS n FROM ("
            "  SELECT canonical_name FROM vendor_identities "
            "  GROUP BY canonical_name HAVING COUNT(*) > 1"
            ") t"
        )
        dupes_cn = conn.fetchone()["n"]
        print(f"Doublons canonical_name : {dupes_cn}")
        if dupes_cn > 0:
            print("  STOP-PB-K : doublons canonical_name · poster immédiatement")
            clean = False

        conn.execute(
            "SELECT COUNT(*) AS n FROM vendor_identities "
            "WHERE vendor_id !~ '^DMS-VND-[A-Z]{3}-[0-9]{4}-[A-Z]$'"
        )
        bad_id = conn.fetchone()["n"]
        print(f"vendor_id malformés : {bad_id}")
        if bad_id > 0:
            print("  STOP-PB-G : IDs malformés · poster immédiatement")
            clean = False

        conn.execute(
            "SELECT region_code, verification_status, COUNT(*) AS n "
            "FROM vendor_identities GROUP BY 1, 2 ORDER BY 1, 2"
        )
        rows = conn.fetchall()
        print("Distribution région x statut :")
        for r in rows:
            print(f"  {r['region_code']} | {r['verification_status']} | {r['n']}")

    return clean


def print_report(report: Wave2Report, dry_run: bool) -> None:
    mode = "DRY-RUN RÉEL (SELECT uniquement · zéro INSERT)" if dry_run else "IMPORT RÉEL"
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"RAPPORT WAVE 2 — {mode}")
    print(sep)
    print(f"Lignes lues              : {report.total_read}")
    print(f"Importés (nouveaux)      : {report.imported}")
    print(f"Doublons détectés en DB  : {report.skipped_duplicate}")
    print(f"Sans nom                 : {report.skipped_no_name}")
    print(f"Zones inconnues (rejetés): {len(report.rejected)}")
    print(f"Taux de rejet            : {report.rejection_rate:.1%}")

    if not dry_run:
        print(
            f"Total DB                 : "
            f"102 + {report.imported} = {102 + report.imported}"
        )
    else:
        print(
            f"Simulation               : "
            f"{report.imported} seraient inserés · "
            f"{report.skipped_duplicate} doublons détectés (état DB actuel)"
        )

    if report.rejected:
        print(f"\nRejetés ({len(report.rejected)}) :")
        for r in report.rejected:
            print(
                f"  x '{r['name']}' "
                f"· zone='{r['zone_raw']}' "
                f"→ norm='{r['zone_normalized']}'"
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

    status = "[DRY-RUN] Simulation propre" if dry_run else "[OK] Import termine"
    print(f"\n{status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETL Wave 2 · 663 fournisseurs Mali · vendor_identities"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Détection doublons par SELECT fingerprint · "
            "zéro INSERT · rapport honnête"
        ),
    )
    args = parser.parse_args()

    _guard_config()

    report = run_wave2_logic(dry_run=args.dry_run)
    print_report(report, dry_run=args.dry_run)

    if not args.dry_run:
        clean = _post_import_validation()
        if not clean:
            raise SystemExit(
                "\nSTOP : anomalies post-import · "
                "voir STOP-PB-F/G/K ci-dessus · poster immédiatement"
            )


if __name__ == "__main__":
    main()
