"""
Tests DB-level — M-CRITERIA-TYPING
ADR-0003 §2.2 Étape 2 — Bloquants CI

psycopg v3 (import psycopg) — pas psycopg2.
Valident les contraintes, triggers et règles métier
au niveau PostgreSQL, pas seulement applicatif.

db_conn   : autocommit=True  — utilisé pour tests simples.
BEGIN/COMMIT SQL explicites pour transactions multi-insert
(triggers DEFERRABLE INITIALLY DEFERRED).
"""

import uuid

import psycopg
import psycopg.errors
import pytest


# ─────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def case_draft(db_conn):
    """Dossier draft — trigger poids inactif."""
    case_id = f"crit-draft-{uuid.uuid4().hex[:8]}"
    with db_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO cases (id, case_type, title, created_at, status)
            VALUES (%s, 'CRITERIA_TEST', %s, NOW()::TEXT, 'draft')
        """, (case_id, 'AO Carburant Bamako Test'))
    yield case_id
    # Nettoyage : criteria d'abord (FK), puis cases.
    # Le DELETE cases peut échouer si une autre table en CASCADE
    # n'est pas accessible (memory_entries) — on l'ignore.
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM criteria WHERE case_id = %s", (case_id,))
    try:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM cases WHERE id = %s", (case_id,))
    except Exception:
        pass


@pytest.fixture
def case_evaluation(db_conn):
    """Dossier evaluation — trigger poids DEFERRED actif au COMMIT."""
    case_id = f"crit-eval-{uuid.uuid4().hex[:8]}"
    with db_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO cases (id, case_type, title, created_at, status)
            VALUES (%s, 'CRITERIA_TEST', %s, NOW()::TEXT, 'evaluation')
        """, (case_id, 'AO Medicaments Test'))
    yield case_id
    # Repasser en 'draft' AVANT de supprimer les critères :
    # le trigger DEFERRED se déclenche au commit implicite du DELETE
    # et verrait somme=0 si le case est encore en 'evaluation'.
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE cases SET status = 'draft' WHERE id = %s",
            (case_id,)
        )
        cur.execute("DELETE FROM criteria WHERE case_id = %s", (case_id,))
    try:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM cases WHERE id = %s", (case_id,))
    except Exception:
        pass


def _insert_criterion(
    cur, case_id, label, weight_pct,
    category='commercial',
    is_essential=False,
    scoring_method='formula',
    org_id='org-test-mali',
    threshold=None,
    canonical_item_id=None,
    currency='XOF',
):
    cur.execute("""
        INSERT INTO criteria (
            case_id, org_id, label, category,
            weight_pct, is_essential, scoring_method,
            threshold, canonical_item_id, currency
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        ) RETURNING id
    """, (
        case_id, org_id, label, category,
        weight_pct, is_essential, scoring_method,
        threshold, canonical_item_id, currency,
    ))
    return cur.fetchone()["id"]


# ─────────────────────────────────────────────────────────────
# GROUPE 1 — Structure
# ─────────────────────────────────────────────────────────────

class TestCriteriaTableStructure:

    def test_table_criteria_existe(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, ('criteria',))
            assert cur.fetchone()["exists"] is True

    def test_enum_category_existe(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type
                    WHERE typname = %s
                )
            """, ('criterion_category_enum',))
            assert cur.fetchone()["exists"] is True

    def test_enum_scoring_method_existe(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type
                    WHERE typname = %s
                )
            """, ('scoring_method_enum',))
            assert cur.fetchone()["exists"] is True

    def test_insertion_nominale(self, db_conn, case_draft):
        with db_conn.cursor() as cur:
            crit_id = _insert_criterion(
                cur, case_draft,
                label='Prix gasoil rendu site Bamako',
                weight_pct=100.0,
                scoring_method='formula',
            )
        assert crit_id is not None

    def test_devise_defaut_xof(self, db_conn, case_draft):
        with db_conn.cursor() as cur:
            crit_id = _insert_criterion(
                cur, case_draft,
                label='Delai livraison',
                weight_pct=100.0,
                scoring_method='paliers',
            )
            cur.execute(
                "SELECT currency FROM criteria WHERE id = %s",
                (crit_id,)
            )
            assert cur.fetchone()["currency"] == 'XOF'

    def test_is_essential_defaut_false(self, db_conn, case_draft):
        with db_conn.cursor() as cur:
            crit_id = _insert_criterion(
                cur, case_draft,
                label='Prix nominal',
                weight_pct=100.0,
                scoring_method='formula',
            )
            cur.execute(
                "SELECT is_essential FROM criteria WHERE id = %s",
                (crit_id,)
            )
            assert cur.fetchone()["is_essential"] is False


# ─────────────────────────────────────────────────────────────
# GROUPE 2 — Contraintes DB
# ─────────────────────────────────────────────────────────────

class TestCriteriaContraintes:

    def test_categorie_invalide_rejetee(self, db_conn, case_draft):
        with pytest.raises(psycopg.errors.InvalidTextRepresentation):
            with db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO criteria (
                        case_id, org_id, label, category,
                        weight_pct, scoring_method
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    case_draft, 'org-test',
                    'Critere invalide', 'prix_invente',
                    50.0, 'formula',
                ))

    def test_poids_negatif_rejete(self, db_conn, case_draft):
        with pytest.raises(psycopg.errors.CheckViolation):
            with db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO criteria (
                        case_id, org_id, label, category,
                        weight_pct, scoring_method
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    case_draft, 'org-test',
                    'Critere negatif', 'commercial',
                    -10.0, 'formula',
                ))

    def test_poids_superieur_100_rejete(self, db_conn, case_draft):
        with pytest.raises(psycopg.errors.CheckViolation):
            with db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO criteria (
                        case_id, org_id, label, category,
                        weight_pct, scoring_method
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    case_draft, 'org-test',
                    'Critere excessif', 'commercial',
                    150.0, 'formula',
                ))

    def test_methode_invalide_rejetee(self, db_conn, case_draft):
        with pytest.raises(psycopg.errors.InvalidTextRepresentation):
            with db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO criteria (
                        case_id, org_id, label, category,
                        weight_pct, scoring_method
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    case_draft, 'org-test',
                    'Critere methode', 'commercial',
                    50.0, 'methode_inventee',
                ))

    def test_fk_case_id_enforced(self, db_conn):
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO criteria (
                        case_id, org_id, label, category,
                        weight_pct, scoring_method
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    'org-test', 'Critere orphelin',
                    'commercial', 50.0, 'formula',
                ))


# ─────────────────────────────────────────────────────────────
# GROUPE 3 — Trigger poids DEFERRED
# BEGIN/COMMIT SQL explicites — db_conn est autocommit=True
# ─────────────────────────────────────────────────────────────

class TestCriteriaTriggerPoidsDEFERRED:

    def test_insertion_partielle_acceptee_en_draft(
        self, db_conn, case_draft
    ):
        """Draft : somme partielle OK — trigger inactif."""
        with db_conn.cursor() as cur:
            _insert_criterion(
                cur, case_draft,
                label='Prix carburant partiel',
                weight_pct=60.0,
                scoring_method='formula',
            )

    def test_trigger_bloque_au_commit_somme_invalide(
        self, db_conn, case_evaluation
    ):
        """
        Evaluation : somme != 100% rejetee AU COMMIT.
        Trigger DEFERRABLE INITIALLY DEFERRED.
        Avec autocommit=True, le commit implicite declenche le trigger.
        """
        with pytest.raises(Exception) as exc_info:
            with db_conn.cursor() as cur:
                _insert_criterion(
                    cur, case_evaluation,
                    label='Prix carburant seul',
                    weight_pct=60.0,
                    scoring_method='formula',
                )
        assert 'CRITERIA-WEIGHT-SUM' in str(exc_info.value)

    def test_transaction_complete_100pct_acceptee(
        self, db_conn, case_evaluation
    ):
        """
        Evaluation : 3 criteres + 1 eliminatoire inseres dans
        une transaction explicite BEGIN/COMMIT → COMMIT OK.
        Scénario AO carburant Mali.
        """
        with db_conn.cursor() as cur:
            cur.execute("BEGIN")
            try:
                _insert_criterion(
                    cur, case_evaluation,
                    label='Agrement ministere transport',
                    weight_pct=0.0,
                    is_essential=True,
                    scoring_method='judgment',
                    threshold=1.0,
                )
                _insert_criterion(
                    cur, case_evaluation,
                    label='Prix gasoil rendu site',
                    weight_pct=60.0,
                    scoring_method='formula',
                )
                _insert_criterion(
                    cur, case_evaluation,
                    label='Delai livraison zone rouge',
                    weight_pct=30.0,
                    scoring_method='paliers',
                )
                _insert_criterion(
                    cur, case_evaluation,
                    label='Capacite stockage futs 200L',
                    weight_pct=10.0,
                    scoring_method='points_scale',
                )
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise

    def test_essentiels_exclus_de_la_somme(
        self, db_conn, case_evaluation
    ):
        """
        Evaluation : eliminatoire a 0% exclu de la somme.
        Scénario AO medicaments — Famille 8 ADR-0002.
        """
        with db_conn.cursor() as cur:
            cur.execute("BEGIN")
            try:
                _insert_criterion(
                    cur, case_evaluation,
                    label='Agrement OMS + DPM Mali',
                    weight_pct=0.0,
                    is_essential=True,
                    scoring_method='judgment',
                    threshold=1.0,
                )
                _insert_criterion(
                    cur, case_evaluation,
                    label='Prix paracetamol 500mg DCI',
                    weight_pct=70.0,
                    scoring_method='formula',
                )
                _insert_criterion(
                    cur, case_evaluation,
                    label='Delai livraison urgence',
                    weight_pct=30.0,
                    scoring_method='paliers',
                )
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise


# ─────────────────────────────────────────────────────────────
# GROUPE 4 — Isolation multi-tenant
# ─────────────────────────────────────────────────────────────

class TestCriteriaIsolationOrg:

    def test_org_ne_voit_pas_criteres_autre_org(
        self, db_conn, case_draft
    ):
        """ONG Bamako != Mine Taoudeni."""
        with db_conn.cursor() as cur:
            _insert_criterion(
                cur, case_draft,
                label='Critere confidentiel ONG',
                weight_pct=100.0,
                org_id='org-ong-bamako',
                scoring_method='formula',
            )
            cur.execute("""
                SELECT COUNT(*) AS cnt FROM criteria
                WHERE case_id = %s AND org_id = %s
            """, (case_draft, 'org-mine-taoudeni'))
            assert cur.fetchone()["cnt"] == 0

            cur.execute("""
                SELECT COUNT(*) AS cnt FROM criteria
                WHERE case_id = %s AND org_id = %s
            """, (case_draft, 'org-ong-bamako'))
            assert cur.fetchone()["cnt"] == 1
