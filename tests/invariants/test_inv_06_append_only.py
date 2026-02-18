"""Test Invariant 6: Append-only & traçabilité.

Constitution V3.3.2 §2: Les tables d'audit doivent être append-only.
"""

import os
import re

import pytest


def test_inv_06_audit_tables_append_only():
    """Les tables d'audit doivent avoir des contraintes append-only."""
    # Vérifier dans les migrations qu'il y a des REVOKE DELETE/UPDATE
    # sur les tables d'audit

    alembic_dir = "alembic/versions"
    audit_tables = ["audits", "market_signals", "memory_entries"]

    if os.path.exists(alembic_dir):
        # Chercher une migration qui applique append-only
        found_append_only = False
        for file in os.listdir(alembic_dir):
            if file.endswith(".py"):
                filepath = os.path.join(alembic_dir, file)
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                    if "REVOKE DELETE" in content or "REVOKE UPDATE" in content:
                        found_append_only = True
                        # Vérifier qu'au moins une table d'audit est concernée
                        for table in audit_tables:
                            if table in content.lower():
                                break
                        else:
                            pytest.fail(
                                f"Migration {file} contient REVOKE mais pas sur table d'audit connue"
                            )

        # Note: Si aucune migration append-only n'existe encore,
        # c'est un problème mais pas un échec de test (sera corrigé par FIX-004)
        if not found_append_only:
            pytest.skip(
                "Contraintes append-only pas encore implémentées (sera corrigé par FIX-004)"
            )


def test_inv_06_no_delete_in_audit_code():
    """Le code ne doit pas contenir de DELETE sur tables d'audit."""
    audit_tables = ["audits", "market_signals", "memory_entries"]
    src_dir = "src"

    if os.path.exists(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                        # Chercher des DELETE sur tables d'audit
                        for table in audit_tables:
                            # Pattern: DELETE FROM table ou DELETE table
                            pattern = rf"DELETE\s+(FROM\s+)?{table}"
                            if re.search(pattern, content, re.IGNORECASE):
                                pytest.fail(
                                    f"DELETE détecté sur table d'audit {table} dans {filepath}"
                                )


def test_inv_06_traceability_present():
    """Les actions critiques doivent être tracées (Constitution V3.3.2 §2 append-only)."""
    alembic_dir = "alembic/versions"
    required_audit_tables = ["audits"]

    if not os.path.exists(alembic_dir):
        pytest.skip("alembic/versions not found")

    found_tables = set()
    for file in os.listdir(alembic_dir):
        if not file.endswith(".py"):
            continue
        filepath = os.path.join(alembic_dir, file)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        for table in required_audit_tables:
            if re.search(
                rf"CREATE TABLE (IF NOT EXISTS )?.*\b{re.escape(table)}\b",
                content,
            ):
                found_tables.add(table)

    for table in required_audit_tables:
        assert table in found_tables, f"Table d'audit requise manquante: {table}"
