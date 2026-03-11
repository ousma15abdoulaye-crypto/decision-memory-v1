"""
Framework Agent-Native DMS (ADR-010)

Contrat obligatoire pour tout agent interagissant avec DMS.

  AgentRunContext  → observabilité (FinOps, durée, statut)
  AgentMemory      → mémoire inter-session (checkpoints)

RÈGLES :
  - Toute interaction LLM DOIT passer par AgentRunContext
  - Tout état inter-session DOIT passer par AgentMemory
  - Aucun agent ne peut écrire directement dans agent_runs_log
    ou agent_checkpoints sans ces classes

CORRECTIONS INTÉGRÉES (audit CTO 2026-03-11) :
  - fetchone()[0] pour extraction UUID (pas str(tuple))
  - __exit__ isolé en try/except — exception originale préservée
  - get_db_url() robuste pour tous variants psycopg
"""

import json
import time
import os
from typing import Any, Dict, Optional

import psycopg
from psycopg.rows import dict_row


# ════════════════════════════════════════════════════════════════
# UTILITAIRE DB
# ════════════════════════════════════════════════════════════════

def get_db_url() -> str:
    """
    Retourne DATABASE_URL normalisé pour psycopg v3.
    Gère : postgres://, postgresql+psycopg://, postgresql+psycopg2://
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise SystemExit("STOP — DATABASE_URL absente")
    # Normalisation : extraire le scheme brut avant tout "+"
    if "://" in url:
        scheme_part, rest = url.split("://", 1)
        base_scheme = scheme_part.split("+")[0]  # postgresql+psycopg2 → postgresql
        url = f"{base_scheme}://{rest}"
    # postgres:// → postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


# ════════════════════════════════════════════════════════════════
# OBSERVABILITÉ / FINOPS
# ════════════════════════════════════════════════════════════════

class AgentRunContext:
    """
    Context Manager — trace l'exécution dans couche_a.agent_runs_log.

    Usage :
        with AgentRunContext(conn, "classify", "cron_daily") as run:
            run.items_in = 100
            run.add_cost(0.045, "mistral-small")
            run.items_ok = 98
            run.items_flagged = 2

    Garanties :
        - Le run est toujours clôturé (done ou failed) même en exception
        - L'exception originale n'est jamais absorbée
        - Un échec du UPDATE de clôture est loggé stderr, pas relancé
    """

    def __init__(
        self,
        conn: psycopg.Connection,
        agent_type: str,
        trigger_event: str,
    ) -> None:
        self.conn = conn
        self.agent_type = agent_type
        self.trigger_event = trigger_event
        self.run_id: str = ""
        self._start: float = 0.0

        # Métriques — à renseigner dans le bloc with
        self.items_in = 0
        self.items_ok = 0
        self.items_flagged = 0
        self.items_error = 0
        self.cost_usd = 0.0
        self.model_used = "unknown"
        self.error_detail: Optional[str] = None

    def __enter__(self) -> "AgentRunContext":
        self._start = time.monotonic()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO couche_a.agent_runs_log
                (agent_type, trigger_event, status)
            VALUES (%s, %s, 'running')
            RETURNING run_id
            """,
            (self.agent_type, self.trigger_event),
        )
        # fetchone() retourne un tuple (uuid_value,) — [0] obligatoire
        row = cur.fetchone()
        self.run_id = str(row[0])
        self.conn.commit()
        return self

    def add_cost(self, usd: float, model: str) -> None:
        """Accumule les coûts LLM — appeler après chaque inférence."""
        self.cost_usd += usd
        self.model_used = model

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        status = "failed" if exc_type else "done"
        duration_ms = int((time.monotonic() - self._start) * 1000)
        if exc_type:
            self.error_detail = str(exc_val)

        # UPDATE isolé : un échec ici ne doit pas masquer l'exception métier
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                UPDATE couche_a.agent_runs_log
                SET status        = %s,
                    items_in      = %s,
                    items_ok      = %s,
                    items_flagged = %s,
                    items_error   = %s,
                    cost_usd      = %s,
                    model_used    = %s,
                    duration_ms   = %s,
                    error_detail  = %s,
                    ended_at      = NOW()
                WHERE run_id = %s
                """,
                (
                    status,
                    self.items_in,
                    self.items_ok,
                    self.items_flagged,
                    self.items_error,
                    self.cost_usd,
                    self.model_used,
                    duration_ms,
                    self.error_detail,
                    self.run_id,
                ),
            )
            self.conn.commit()
        except Exception as update_err:
            import sys
            print(
                f"[AgentRunContext] WARNING: clôture run {self.run_id} "
                f"échouée: {update_err}",
                file=sys.stderr,
            )
            try:
                self.conn.rollback()
            except Exception:
                pass

        return False  # Ne jamais absorber l'exception originale


# ════════════════════════════════════════════════════════════════
# MÉMOIRE PERSISTANTE
# ════════════════════════════════════════════════════════════════

class AgentMemory:
    """
    Interface mémoire inter-session — couche_a.agent_checkpoints.

    Permet à un agent de reprendre où il s'est arrêté
    entre deux sessions ou deux runs.

    Usage :
        mem = AgentMemory(conn)
        ckpt_id = mem.save_checkpoint(
            "thread_001", "market_signal", "step_analyse",
            {"items_processed": 42, "last_zone": "Mopti"},
            tokens=250,
        )
        ckpt = mem.get_latest_checkpoint("thread_001")
        # ckpt["state_json"]["items_processed"] == 42
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def save_checkpoint(
        self,
        thread_id: str,
        agent_type: str,
        step_name: str,
        state: Dict[str, Any],
        tokens: int = 0,
    ) -> str:
        """
        Persiste un checkpoint. Retourne le checkpoint_id (UUID string).
        Lève psycopg.Error si agent_type n'est pas dans le CHECK constraint.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO couche_a.agent_checkpoints
                (thread_id, agent_type, step_name, state_json, token_count)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING checkpoint_id
            """,
            (thread_id, agent_type, step_name, json.dumps(state), tokens),
        )
        # fetchone() retourne un tuple (uuid_value,) — [0] obligatoire
        row = cur.fetchone()
        checkpoint_id = str(row[0])
        self.conn.commit()
        return checkpoint_id

    def get_latest_checkpoint(
        self,
        thread_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retourne le checkpoint le plus récent pour ce thread_id.
        Retourne None si aucun checkpoint trouvé.
        state_json est retourné comme dict Python (déjà désérialisé par psycopg).
        """
        cur = self.conn.cursor(row_factory=dict_row)
        cur.execute(
            """
            SELECT state_json,
                   step_name,
                   created_at,
                   token_count
            FROM couche_a.agent_checkpoints
            WHERE thread_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (thread_id,),
        )
        return cur.fetchone()
