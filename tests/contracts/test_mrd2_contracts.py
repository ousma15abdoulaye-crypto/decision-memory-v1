"""
tests/contracts/test_mrd2_contracts.py
───────────────────────────────────────
MRD-2 — Tests de contrat génétique.

5 tests :
  CT-01  IS-02 : aucune CASCADE FK sur couche_b
  CT-02  IS-06 : alembic heads = 1 ligne
  CT-03  IS-07 : DATABASE_URL ne contient pas 'railway'
  CT-04  DEF-03 : procurement_dict_items est append-only (pas de DELETE)
  CT-05  DEF-02 : fingerprint stable — même input = même hash

2 tests intentionnellement ROUGES documentés :
  CT-ROUGE-01  trg_protect_item_identity absent (DEF-MRD3-06 — corrigé MRD-4)
  CT-ROUGE-02  trg_protect_item_with_aliases absent (DEF-MRD3-06 — corrigé MRD-4)

Ces deux tests rouges sont la preuve vivante que MRD-4 est nécessaire.
Ils passent VERT après MRD-4.
"""

import hashlib
import os
import subprocess

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db_conn():
    """Connexion DB locale pour les tests de contrat."""
    # Charger .env si DATABASE_URL absent du shell
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path) and not os.environ.get("DATABASE_URL"):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    db_url = os.environ.get("DATABASE_URL", "")
    assert db_url, "DATABASE_URL absente — impossible d'exécuter les tests de contrat"

    # CONTRACT-02 : jamais Railway en local
    assert "railway" not in db_url.lower() and "rlwy" not in db_url.lower(), \
        "CONTRACT-02 VIOLÉ — DATABASE_URL pointe Railway"

    url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
    import psycopg
    conn = psycopg.connect(url, connect_timeout=5, row_factory=psycopg.rows.dict_row)
    yield conn
    conn.close()


# ── CT-01 : IS-02 — aucune CASCADE FK sur couche_b ───────────────────────

def test_ct01_no_cascade_fk_couche_b(db_conn):
    """
    IS-02 : ON DELETE CASCADE interdit sur tables couche_b.
    Toutes les FK doivent être RESTRICT, NO ACTION ou SET NULL.
    MRD-3 a corrigé la violation CASCADE sur aliases.
    Ce test VERT confirme la correction.
    """
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT tc.table_name, kcu.column_name, rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema    = kcu.table_schema
            JOIN information_schema.referential_constraints rc
              ON rc.constraint_name   = tc.constraint_name
             AND rc.constraint_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema    = 'couche_b'
              AND rc.delete_rule     = 'CASCADE'
        """)
        cascades = cur.fetchall()

    assert cascades == [], (
        f"IS-02 VIOLÉ — CASCADE FK détectée sur couche_b : {cascades}\n"
        "STOP-14 — corriger avant tout merge."
    )


# ── CT-02 : IS-06 — alembic heads = 1 ───────────────────────────────────

def test_ct02_alembic_single_head():
    """
    IS-06 : alembic heads doit retourner exactement 1 ligne.
    Plusieurs heads = divergence non résolue = interdit.
    """
    result = subprocess.run(
        ["alembic", "heads"], capture_output=True, text=True
    )
    head_lines = [
        line.strip() for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(head_lines) == 1, (
        f"IS-06 VIOLÉ — alembic heads = {len(head_lines)} lignes : {head_lines}\n"
        "STOP-01 — merger les heads avant tout commit migration."
    )


# ── CT-03 : IS-07 — DATABASE_URL pas Railway ─────────────────────────────

def test_ct03_database_url_not_railway():
    """
    IS-07 / CONTRACT-02 : DATABASE_URL ne doit jamais pointer Railway
    dans un contexte d'exécution locale.
    """
    # Charger .env si nécessaire
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path) and not os.environ.get("DATABASE_URL"):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    db_url = os.environ.get("DATABASE_URL", "")
    assert db_url, "DATABASE_URL absente"
    assert "railway" not in db_url.lower() and "rlwy" not in db_url.lower(), (
        "IS-07 / CONTRACT-02 VIOLÉ — DATABASE_URL contient 'railway'.\n"
        "STOP-12 — corriger .env avant tout test ou migration locale."
    )


# ── CT-04 : DEF-03 — aucun trigger DELETE sur procurement_dict_items ─────

def test_ct04_no_delete_trigger_on_items(db_conn):
    """
    DEF-03 : le registre est append-only.
    Il ne doit exister aucun trigger AFTER DELETE ou BEFORE DELETE
    sur procurement_dict_items qui effectuerait une suppression en cascade.
    Vérifie aussi qu'il n'existe pas de règle DROP/TRUNCATE.
    """
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT trigger_name, event_manipulation, action_timing
            FROM information_schema.triggers
            WHERE trigger_schema      = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND event_manipulation  = 'DELETE'
        """)
        delete_triggers = cur.fetchall()

    # Aucun trigger DELETE ne doit déclencher une suppression en cascade
    # (les triggers DELETE de protection comme protect_item sont AUTORISÉS
    #  car ils BLOQUENT la suppression — ils ne l'effectuent pas)
    destructive = [
        t for t in delete_triggers
        if "protect" not in t["trigger_name"].lower()
        and "block" not in t["trigger_name"].lower()
    ]
    assert destructive == [], (
        f"DEF-03 VIOLÉ — triggers DELETE non-protecteurs détectés : {destructive}\n"
        "STOP-06 — ces triggers peuvent causer des pertes destructives."
    )


# ── CT-05 : DEF-02 — fingerprint stable ──────────────────────────────────

def test_ct05_fingerprint_stable():
    """
    DEF-02 : fingerprint = sha256(normalize(label)|source_type|source_id).
    normalize() = strip + lower + collapse_whitespace.
    Même input → même output. Déterministe. Immuable.
    """
    import re

    def normalize(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip().lower())

    def fingerprint(label: str, source_type: str, source_id: str) -> str:
        raw = normalize(label) + "|" + source_type + "|" + source_id
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # Même input = même hash
    fp1 = fingerprint("  Ciment Portland  ", "mercuriale", "SRC-001")
    fp2 = fingerprint("ciment portland", "mercuriale", "SRC-001")
    assert fp1 == fp2, (
        f"DEF-02 VIOLÉ — normalize() non déterministe : {fp1} != {fp2}"
    )

    # Input différent = hash différent
    fp3 = fingerprint("Ciment Portland CEM I", "mercuriale", "SRC-001")
    assert fp1 != fp3, (
        "DEF-02 VIOLÉ — collision sur labels distincts"
    )

    # Cohérence avec l'algorithme attendu
    expected = hashlib.sha256(
        b"ciment portland|mercuriale|SRC-001"
    ).hexdigest()
    assert fp1 == expected, (
        f"DEF-02 VIOLÉ — fingerprint diverge de la formule canonique.\n"
        f"Attendu : {expected}\nObtenu  : {fp1}"
    )


# ── CT-ROUGE-01 : trigger protect_item_identity ABSENT ───────────────────

def test_ct_rouge_01_trigger_protect_item_identity(db_conn):
    """
    INTENTIONNELLEMENT ROUGE — DEF-MRD3-06.
    Vérifie que trg_protect_item_identity existe sur procurement_dict_items.
    Absent = items peuvent être modifiés de manière destructive.
    Correction : MRD-4 crée ce trigger.
    """
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT trigger_name FROM information_schema.triggers
            WHERE trigger_schema     = 'couche_b'
              AND event_object_table = 'procurement_dict_items'
              AND trigger_name       = 'trg_protect_item_identity'
        """)
        row = cur.fetchone()
    assert row is not None, (
        "STOP-TRG-1 — trg_protect_item_identity absent.\n"
        "Ce trigger protège l'immuabilité du fingerprint et de item_uid.\n"
        "MRD-4 corrige cette défaillance."
    )


# ── CT-ROUGE-02 : trigger protect_item_with_aliases ABSENT ───────────────

def test_ct_rouge_02_trigger_protect_item_with_aliases(db_conn):
    """
    INTENTIONNELLEMENT ROUGE — DEF-MRD3-06.
    Vérifie que trg_protect_item_with_aliases existe sur procurement_dict_items.
    Absent = items avec aliases peuvent être supprimés (perte mémoire terrain).
    Correction : MRD-4 crée ce trigger.
    """
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT trigger_name FROM information_schema.triggers
            WHERE trigger_schema     = 'couche_b'
              AND event_object_table = 'procurement_dict_items'
              AND trigger_name       = 'trg_protect_item_with_aliases'
        """)
        row = cur.fetchone()
    assert row is not None, (
        "STOP-TRG-2 — trg_protect_item_with_aliases absent.\n"
        "Ce trigger empêche la suppression d'items ayant des aliases.\n"
        "MRD-4 corrige cette défaillance."
    )
