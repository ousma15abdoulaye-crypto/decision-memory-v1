"""
Tests M10B — Agent-Native Foundation (ADR-010)

Couverture :
  T1  AgentRunContext — run successful → status=done, métriques OK
  T2  AgentRunContext — exception → status=failed, error_detail peuplé
  T3  AgentMemory — save + retrieve checkpoint
  T4  agent_runs_log APPEND-ONLY — DELETE déclenche exception ADR-010

RÈGLES :
  - Tests locaux uniquement (skip sur Railway)
  - Pas de mock — vrai psycopg, vraie DB locale
  - Chaque test est indépendant (pas de dépendance inter-tests)
"""

import os
from pathlib import Path

import psycopg
import pytest

from src.couche_a.agents.framework import AgentMemory, AgentRunContext

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

DB = os.environ.get("DATABASE_URL", "")


@pytest.fixture(scope="module")
def conn():
    """
    Connexion locale uniquement.
    Skip si Railway détecté (rlwy.net ou railway.app).
    """
    if not DB:
        pytest.skip("DATABASE_URL absente")
    if "rlwy.net" in DB.lower() or "railway.app" in DB.lower():
        pytest.skip("Tests locaux uniquement — Railway exclu")
    # Normaliser URL pour psycopg
    url = DB
    if "://" in url:
        scheme_part, rest = url.split("://", 1)
        url = f"{scheme_part.split('+')[0]}://{rest}"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    c = psycopg.connect(url)
    yield c
    c.close()


# ── T1 — Run successful ──────────────────────────────────────────


def test_agent_run_context_success(conn):
    """
    Un AgentRunContext qui se termine sans exception
    doit créer un run avec status='done' et les métriques correctes.
    """
    with AgentRunContext(conn, "classify", "test_t1_success") as run:
        run.items_in = 10
        run.items_ok = 10
        run.add_cost(0.01, "mistral-small")

    cur = conn.cursor()
    cur.execute(
        """
        SELECT status, cost_usd, model_used, duration_ms
        FROM couche_a.agent_runs_log
        WHERE run_id = %s
        """,
        (run.run_id,),
    )
    row = cur.fetchone()
    assert row is not None, "Run introuvable en DB après __exit__"
    assert row[0] == "done", f"status attendu 'done', obtenu '{row[0]}'"
    assert float(row[1]) == pytest.approx(
        0.01, abs=1e-5
    ), f"cost_usd attendu 0.01, obtenu {row[1]}"
    assert row[2] == "mistral-small", f"model_used incorrect : {row[2]}"
    assert row[3] is not None, "duration_ms ne doit pas être NULL"
    assert row[3] >= 0, f"duration_ms négatif : {row[3]}"


# ── T2 — Run avec exception ──────────────────────────────────────


def test_agent_run_context_failure(conn):
    """
    Un AgentRunContext qui reçoit une exception
    doit créer un run avec status='failed' et error_detail peuplé.
    L'exception doit remonter normalement.
    """
    run_ref = None
    with pytest.raises(ValueError, match="Erreur simulée M10B"):
        with AgentRunContext(conn, "query", "test_t2_failure") as run:
            run_ref = run
            run.items_in = 1
            raise ValueError("Erreur simulée M10B")

    assert run_ref is not None
    cur = conn.cursor()
    cur.execute(
        """
        SELECT status, error_detail
        FROM couche_a.agent_runs_log
        WHERE run_id = %s
        """,
        (run_ref.run_id,),
    )
    row = cur.fetchone()
    assert row is not None, "Run introuvable en DB"
    assert row[0] == "failed", f"status attendu 'failed', obtenu '{row[0]}'"
    assert row[1] is not None, "error_detail ne doit pas être NULL"
    assert "Erreur simulée M10B" in row[1], f"error_detail incorrect : {row[1]}"


# ── T3 — Mémoire checkpoint ──────────────────────────────────────


def test_agent_memory_save_and_retrieve(conn):
    """
    AgentMemory doit persister un checkpoint et le retrouver
    avec state_json intact.
    """
    mem = AgentMemory(conn)
    tid = "thread_test_m10b_t3"

    ckpt_id = mem.save_checkpoint(
        thread_id=tid,
        agent_type="market_signal",
        step_name="step_analyse",
        state={"items_processed": 42, "last_zone": "Mopti"},
        tokens=250,
    )
    assert ckpt_id is not None, "save_checkpoint doit retourner un UUID string"
    assert len(ckpt_id) == 36, f"UUID malformé : {ckpt_id}"

    ckpt = mem.get_latest_checkpoint(tid)
    assert ckpt is not None, "Checkpoint introuvable"
    assert ckpt["step_name"] == "step_analyse", "step_name incorrect"
    assert ckpt["state_json"]["items_processed"] == 42, "state_json altéré"
    assert ckpt["state_json"]["last_zone"] == "Mopti", "state_json altéré"
    assert ckpt["token_count"] == 250, "token_count incorrect"


# ── T4 — APPEND-ONLY guard ───────────────────────────────────────


def test_agent_runs_append_only(conn):
    """
    Toute tentative de DELETE sur agent_runs_log
    doit lever une exception PostgreSQL contenant 'APPEND-ONLY'.
    Vérifie l'invariant ADR-010.
    """
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO couche_a.agent_runs_log
            (agent_type, trigger_event, status)
        VALUES ('classify', 'test_t4_nodelete', 'done')
        RETURNING run_id
        """)
    # fetchone() retourne un tuple — [0] pour la valeur
    run_id = cur.fetchone()[0]
    conn.commit()

    with pytest.raises(Exception, match="APPEND-ONLY"):
        cur.execute(
            "DELETE FROM couche_a.agent_runs_log WHERE run_id = %s",
            (run_id,),
        )
        conn.commit()

    # Rollback obligatoire après exception psycopg
    conn.rollback()
