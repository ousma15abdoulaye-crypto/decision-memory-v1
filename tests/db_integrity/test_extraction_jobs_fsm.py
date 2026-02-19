# tests/db_integrity/test_extraction_jobs_fsm.py
"""
Tests DB-level — M-EXTRACTION-ENGINE
Machine d'état extraction_jobs + doctrine §9.
🔴 TOUS BLOQUANTS CI.
Constitution V3.3.2 §8 (machine d'état) + §9 (doctrine échec).
"""
import pytest

# ── Helpers locaux ───────────────────────────────────────────────

def _insert_job(cur, status="pending", method="native_pdf",
                sla_class="A"):
    """Insère un job de test. Retourne son id."""
    cur.execute("""
        INSERT INTO extraction_jobs
            (document_id, method, sla_class, status)
        SELECT id, %s, %s, %s
        FROM documents
        LIMIT 1
        RETURNING id
    """, (method, sla_class, status))
    row = cur.fetchone()
    if row is None:
        pytest.skip(
            "Aucun document en DB — M-DOCS-CORE requis."
        )
    return row["id"]


def _insert_processing_job(cur):
    """Insère un job en état processing avec started_at."""
    cur.execute("""
        INSERT INTO extraction_jobs
            (document_id, method, sla_class,
             status, started_at)
        SELECT id, 'native_pdf', 'A', 'processing', NOW()
        FROM documents
        LIMIT 1
        RETURNING id
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("Aucun document en DB.")
    return row["id"]


# ── Classe 1 — Transitions valides ──────────────────────────────

class TestFSMTransitionsValides:
    """§8 : transitions autorisées — aucune exception attendue."""

    def test_pending_to_processing(self, db_transaction):
        job_id = _insert_job(db_transaction, status="pending")
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'processing'
            WHERE id = %s
        """, (job_id,))
        db_transaction.execute(
            "SELECT status FROM extraction_jobs WHERE id = %s",
            (job_id,)
        )
        assert db_transaction.fetchone()["status"] == "processing"

    def test_pending_to_failed(self, db_transaction):
        job_id = _insert_job(db_transaction, status="pending")
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'failed'
            WHERE id = %s
        """, (job_id,))
        db_transaction.execute(
            "SELECT status FROM extraction_jobs WHERE id = %s",
            (job_id,)
        )
        assert db_transaction.fetchone()["status"] == "failed"

    def test_processing_to_done(self, db_transaction):
        job_id = _insert_processing_job(db_transaction)
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'done'
            WHERE id = %s
        """, (job_id,))
        db_transaction.execute(
            "SELECT status FROM extraction_jobs WHERE id = %s",
            (job_id,)
        )
        assert db_transaction.fetchone()["status"] == "done"

    def test_processing_to_failed(self, db_transaction):
        job_id = _insert_processing_job(db_transaction)
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'failed'
            WHERE id = %s
        """, (job_id,))
        db_transaction.execute(
            "SELECT status FROM extraction_jobs WHERE id = %s",
            (job_id,)
        )
        assert db_transaction.fetchone()["status"] == "failed"

    def test_failed_to_pending_retry(self, db_transaction):
        job_id = _insert_job(db_transaction, status="failed")
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'pending',
                retry_count = retry_count + 1
            WHERE id = %s
        """, (job_id,))
        db_transaction.execute(
            """SELECT status, retry_count
               FROM extraction_jobs WHERE id = %s""",
            (job_id,)
        )
        row = db_transaction.fetchone()
        assert row["status"] == "pending"
        assert row["retry_count"] == 1

    def test_same_status_no_error(self, db_transaction):
        """Même statut → trigger ignoré (WHEN guard)."""
        job_id = _insert_job(db_transaction, status="pending")
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'pending'
            WHERE id = %s
        """, (job_id,))


# ── Classe 2 — Transitions invalides ────────────────────────────

class TestFSMTransitionsInvalides:
    """§8 : transitions interdites — exception obligatoire."""

    def test_pending_to_done_interdit(self, db_transaction):
        job_id = _insert_job(db_transaction, status="pending")
        with pytest.raises(Exception) as exc:
            db_transaction.execute("""
                UPDATE extraction_jobs
                SET status = 'done'
                WHERE id = %s
            """, (job_id,))
        err = str(exc.value).lower()
        assert any(kw in err for kw in
                   ["invalide", "§8", "transition", "interdit"])

    def test_done_to_pending_interdit(self, db_transaction):
        job_id = _insert_job(db_transaction, status="done")
        with pytest.raises(Exception):
            db_transaction.execute("""
                UPDATE extraction_jobs
                SET status = 'pending'
                WHERE id = %s
            """, (job_id,))

    def test_done_to_processing_interdit(self, db_transaction):
        job_id = _insert_job(db_transaction, status="done")
        with pytest.raises(Exception):
            db_transaction.execute("""
                UPDATE extraction_jobs
                SET status = 'processing'
                WHERE id = %s
            """, (job_id,))

    def test_done_to_failed_interdit(self, db_transaction):
        job_id = _insert_job(db_transaction, status="done")
        with pytest.raises(Exception):
            db_transaction.execute("""
                UPDATE extraction_jobs
                SET status = 'failed'
                WHERE id = %s
            """, (job_id,))

    def test_processing_to_pending_interdit(self, db_transaction):
        job_id = _insert_processing_job(db_transaction)
        with pytest.raises(Exception):
            db_transaction.execute("""
                UPDATE extraction_jobs
                SET status = 'pending'
                WHERE id = %s
            """, (job_id,))


# ── Classe 3 — Horodatage automatique ───────────────────────────

class TestHorodatageAutomatique:
    """Le trigger horodate automatiquement les transitions."""

    def test_started_at_null_avant_processing(
        self, db_transaction
    ):
        job_id = _insert_job(db_transaction, status="pending")
        db_transaction.execute(
            "SELECT started_at FROM extraction_jobs WHERE id = %s",
            (job_id,)
        )
        assert db_transaction.fetchone()["started_at"] is None

    def test_started_at_set_on_processing(self, db_transaction):
        job_id = _insert_job(db_transaction, status="pending")
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'processing'
            WHERE id = %s
        """, (job_id,))
        db_transaction.execute(
            "SELECT started_at FROM extraction_jobs WHERE id = %s",
            (job_id,)
        )
        assert db_transaction.fetchone()["started_at"] is not None

    def test_completed_at_set_on_done(self, db_transaction):
        job_id = _insert_processing_job(db_transaction)
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'done'
            WHERE id = %s
        """, (job_id,))
        db_transaction.execute(
            """SELECT completed_at, duration_ms
               FROM extraction_jobs WHERE id = %s""",
            (job_id,)
        )
        row = db_transaction.fetchone()
        assert row["completed_at"] is not None
        assert row["duration_ms"] is not None
        assert row["duration_ms"] >= 0

    def test_completed_at_set_on_failed(self, db_transaction):
        job_id = _insert_processing_job(db_transaction)
        db_transaction.execute("""
            UPDATE extraction_jobs
            SET status = 'failed'
            WHERE id = %s
        """, (job_id,))
        db_transaction.execute(
            "SELECT completed_at FROM extraction_jobs WHERE id = %s",
            (job_id,)
        )
        assert db_transaction.fetchone()["completed_at"] is not None


# ── Classe 4 — Contraintes CHECK ────────────────────────────────

class TestContraintesCheck:
    """Valeurs hors liste → rejetées par CHECK PostgreSQL."""

    def test_status_invalide_rejete(self, db_transaction):
        with pytest.raises(Exception):
            db_transaction.execute("""
                INSERT INTO extraction_jobs
                    (document_id, method, sla_class, status)
                SELECT id, 'native_pdf', 'A', 'INVENTED'
                FROM documents LIMIT 1
            """)

    def test_method_invalide_rejetee(self, db_transaction):
        with pytest.raises(Exception):
            db_transaction.execute("""
                INSERT INTO extraction_jobs
                    (document_id, method, sla_class)
                SELECT id, 'word_magic', 'A'
                FROM documents LIMIT 1
            """)

    def test_sla_class_invalide_rejetee(self, db_transaction):
        with pytest.raises(Exception):
            db_transaction.execute("""
                INSERT INTO extraction_jobs
                    (document_id, method, sla_class)
                SELECT id, 'native_pdf', 'C'
                FROM documents LIMIT 1
            """)

    def test_error_code_invalide_rejete(self, db_transaction):
        with pytest.raises(Exception):
            db_transaction.execute("""
                INSERT INTO extraction_errors
                    (document_id, error_code, error_detail)
                SELECT id, 'INVENTED_CODE', 'test'
                FROM documents LIMIT 1
            """)


# ── Classe 5 — Doctrine §9 ───────────────────────────────────────

class TestDoctrineEchec:
    """§9 : échec explicite, requires_human par défaut."""

    def test_requires_human_default_true(self, db_transaction):
        db_transaction.execute("""
            INSERT INTO extraction_errors
                (document_id, error_code, error_detail)
            SELECT id, 'OCR_FAILED',
                   'Tesseract timeout après 120s'
            FROM documents LIMIT 1
            RETURNING requires_human
        """)
        row = db_transaction.fetchone()
        assert row is not None
        assert row["requires_human"] is True

    def test_error_linked_to_document(self, db_transaction):
        db_transaction.execute("""
            INSERT INTO extraction_errors
                (document_id, error_code, error_detail)
            SELECT id, 'CORRUPT_FILE',
                   'Magic bytes invalides'
            FROM documents LIMIT 1
            RETURNING document_id
        """)
        row = db_transaction.fetchone()
        assert row is not None
        assert row["document_id"] is not None

    def test_tous_codes_valides_acceptes(self, db_transaction):
        codes_valides = [
            "UNSUPPORTED_FORMAT",
            "CORRUPT_FILE",
            "OCR_FAILED",
            "TIMEOUT_SLA_A",
            "LOW_CONFIDENCE",
            "EMPTY_CONTENT",
            "PARSE_ERROR",
        ]
        for code in codes_valides:
            db_transaction.execute("""
                INSERT INTO extraction_errors
                    (document_id, error_code, error_detail)
                SELECT id, %s, %s
                FROM documents LIMIT 1
            """, (code, f"test code {code}"))

    def test_job_id_optionnel_accepte(self, db_transaction):
        db_transaction.execute("""
            INSERT INTO extraction_errors
                (document_id, error_code,
                 error_detail, job_id)
            SELECT id, 'PARSE_ERROR',
                   'Erreur sans job', NULL
            FROM documents LIMIT 1
            RETURNING id
        """)
        assert db_transaction.fetchone() is not None
