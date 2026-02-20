# tests/db_integrity/test_extraction_jobs_fsm.py
"""
Tests DB-level — M-EXTRACTION-ENGINE
Machine d'état extraction_jobs + doctrine §9.
🔴 TOUS BLOQUANTS CI.
Constitution V3.3.2 §8 (machine d'état) + §9 (doctrine échec).
"""

import pytest

# ── Helpers locaux ───────────────────────────────────────────────


def _insert_job(cur, status="pending", method="native_pdf", sla_class="A"):
    """Insère un job de test. Retourne son id."""
    cur.execute(
        """
        INSERT INTO extraction_jobs
            (document_id, method, sla_class, status)
        SELECT id, %s, %s, %s
        FROM documents
        LIMIT 1
        RETURNING id
    """,
        (method, sla_class, status),
    )
    row = cur.fetchone()
    if row is None:
        pytest.skip("Aucun document en DB — M-DOCS-CORE requis.")
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
        db_transaction.execute(
            """
            UPDATE extraction_jobs
            SET status = 'processing'
            WHERE id = %s
        """,
            (job_id,),
        )
        db_transaction.execute(
            "SELECT status FROM extraction_jobs WHERE id = %s", (job_id,)
        )
        assert db_transaction.fetchone()["status"] == "processing"

    def test_pending_to_failed(self, db_transaction):
        job_id = _insert_job(db_transaction, status="pending")
        db_transaction.execute(
            """
            UPDATE extraction_jobs
            SET status = 'failed'
            WHERE id = %s
        """,
            (job_id,),
        )
        db_transaction.execute(
            "SELECT status FROM extraction_jobs WHERE id = %s", (job_id,)
        )
        assert db_transaction.fetchone()["status"] == "failed"

    def test_processing_to_done(self, db_transaction):
        job_id = _insert_processing_job(db_transaction)
        db_transaction.execute(
            """
            UPDATE extraction_jobs
            SET status = 'done'
            WHERE id = %s
        """,
            (job_id,),
        )
        db_transaction.execute(
            "SELECT status FROM extraction_jobs WHERE id = %s", (job_id,)
        )
        assert db_transaction.fetchone()["status"] == "done"

    def test_processing_to_failed(self, db_transaction):
        job_id = _insert_processing_job(db_transaction)
        db_transaction.execute(
            """
            UPDATE extraction_jobs
            SET status = 'failed'
            WHERE id = %s
        """,
            (job_id,),
        )
        db_transaction.execute(
            "SELECT status FROM extraction_jobs WHERE id = %s", (job_id,)
        )
        assert db_transaction.fetchone()["status"] == "failed"

    def test_failed_to_pending_retry(self, db_transaction):
        job_id = _insert_job(db_transaction, status="failed")
        db_transaction.execute(
            """
            UPDATE extraction_jobs
            SET status = 'pending',
                retry_count = retry_count + 1
            WHERE id = %s
        """,
            (job_id,),
        )
        db_transaction.execute(
            """SELECT status, retry_count
               FROM extraction_jobs WHERE id = %s""",
            (job_id,),
        )
        row = db_transaction.fetchone()
        assert row["status"] == "pending"
        assert row["retry_count"] == 1

    def test_same_status_no_error(self, db_transaction):
        """Même statut → trigger ignoré (WHEN guard)."""
        job_id = _insert_job(db_transaction, status="pending")
        db_transaction.execute(
            """
            UPDATE extraction_jobs
            SET status = 'pending'
            WHERE id = %s
        """,
            (job_id,),
        )


# ── Classe 2 — Transitions invalides ────────────────────────────


class TestFSMTransitionsInvalides:
    """§8 : transitions interdites — exception obligatoire."""

    def test_pending_to_done_interdit(self, db_transaction):
        job_id = _insert_job(db_transaction, status="pending")
        with pytest.raises(Exception) as exc:
            db_transaction.execute(
                """
                UPDATE extraction_jobs
                SET status = 'done'
                WHERE id = %s
            """,
                (job_id,),
            )
        err = str(exc.value).lower()
        assert any(kw in err for kw in ["invalide", "§8", "transition", "interdit"])

    def test_done_to_pending_interdit(self, db_transaction):
        job_id = _insert_job(db_transaction, status="done")
        with pytest.raises(Exception):
            db_transaction.execute(
                """
                UPDATE extraction_jobs
                SET status = 'pending'
                WHERE id
