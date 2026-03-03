"""
Tests seed vendors M4 — dry-run + import réel.
Prouve que l'ETL charge les fichiers source correctement.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FILES = [
    Path("data/imports/m4/Supplier DATA BAMAKO.xlsx"),
    Path("data/imports/m4/Supplier DATA Mopti et autres zones nords.xlsx"),
]


def _files_present() -> bool:
    return all(f.exists() for f in FILES)


@pytest.mark.skipif(
    not _files_present(),
    reason="Fichiers xlsx source absents de data/imports/m4/",
)
def test_etl_dry_run_zero_db_write(db_conn):
    """Dry-run ne doit produire aucune écriture en DB."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM vendors")
        count_before = cur.fetchone()["cnt"]

    from scripts.etl_vendors_m4 import run_etl

    report = run_etl(dry_run=True)

    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM vendors")
        count_after = cur.fetchone()["cnt"]

    assert count_after == count_before, "Dry-run a écrit en DB"
    assert report.total_read > 0, "Dry-run n'a lu aucune ligne"
    assert report.imported > 0, "Dry-run n'a traité aucune ligne valide"


@pytest.mark.skipif(
    not _files_present(),
    reason="Fichiers xlsx source absents de data/imports/m4/",
)
def test_etl_real_import_vendor_ids_format(db_conn):
    """Après import réel, tous les vendor_ids doivent commencer par DMS-VND-."""
    # Nettoyage avant le test
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'EXCEL_M4'")

    from scripts.etl_vendors_m4 import run_etl

    report = run_etl(dry_run=False)

    assert report.imported > 0, "Aucun vendor importé"
    for vid in report.vendor_ids:
        assert vid.startswith("DMS-VND-"), f"Format invalide : {vid}"

    # Nettoyage après le test
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'EXCEL_M4'")


@pytest.mark.skipif(
    not _files_present(),
    reason="Fichiers xlsx source absents de data/imports/m4/",
)
def test_etl_real_import_vendor_ids_unique(db_conn):
    """Les vendor_ids générés par l'ETL doivent être uniques."""
    # Nettoyage avant le test
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'EXCEL_M4'")

    from scripts.etl_vendors_m4 import run_etl

    report = run_etl(dry_run=False)

    assert len(report.vendor_ids) == len(
        set(report.vendor_ids)
    ), "Doublons dans les vendor_ids générés"

    # Nettoyage après le test
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'EXCEL_M4'")


@pytest.mark.skipif(
    not _files_present(),
    reason="Fichiers xlsx source absents de data/imports/m4/",
)
def test_etl_region_distribution_coherent(db_conn):
    """La distribution des régions doit contenir BKO et MPT au minimum."""
    # Nettoyage avant le test
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'EXCEL_M4'")

    from scripts.etl_vendors_m4 import run_etl

    run_etl(dry_run=False)

    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT region_code, COUNT(*) AS cnt
            FROM vendors
            WHERE source = 'EXCEL_M4'
            GROUP BY region_code
            """)
        rows = cur.fetchall()

    regions = {r["region_code"] for r in rows}
    assert "BKO" in regions, "Aucun vendor BKO dans l'import"
    assert "MPT" in regions, "Aucun vendor MPT dans l'import"

    # Nettoyage après le test
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM vendors WHERE source = 'EXCEL_M4'")
