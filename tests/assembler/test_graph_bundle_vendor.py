"""Regroupement fournisseur Pass -1 — clé de bundle (ZIP dossier vs heuristique)."""

from __future__ import annotations

from src.assembler.graph import resolve_bundle_vendor_key


def test_resolve_uses_top_level_zip_folder() -> None:
    assert (
        resolve_bundle_vendor_key("", "ACME SARL/Offre_technique.docx") == "ACME SARL"
    )
    assert resolve_bundle_vendor_key("", "Lot1/BATE/Doc.docx") == "Lot1"


def test_resolve_flat_filename_falls_back_to_stem_prefix() -> None:
    assert resolve_bundle_vendor_key("", "BECATE_offre.docx") == "BECATE"


def test_resolve_flat_uses_filename_stem_prefix() -> None:
    # Sans dossier ZIP : préfixe avant "_" dans le nom de fichier (stem entier sinon).
    assert resolve_bundle_vendor_key("", "x.docx") == "x"


def test_resolve_line_with_sarl_beats_filename_when_flat() -> None:
    text = "SOCIETE EXAMPLE SARL\nSuite du document"
    assert resolve_bundle_vendor_key(text, "foo.docx").startswith(
        "SOCIETE EXAMPLE SARL"
    )
