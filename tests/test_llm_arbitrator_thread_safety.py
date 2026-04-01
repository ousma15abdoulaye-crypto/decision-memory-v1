"""
Tests thread-safety LLMArbitrator.

T1 : get_arbitrator() retourne la même instance depuis plusieurs threads
     (singleton, double-checked locking). Comparaison par identité (is),
     pas par id() pour éviter les faux négatifs si l'instance est libérée.
T2 : _tls.last_cost est isolé par thread — un thread ne voit pas le coût
     du thread voisin.
T3 : reset_arbitrator() réinitialise proprement le singleton.
"""

from __future__ import annotations

import threading

_BARRIER_TIMEOUT_S = 5.0
_JOIN_TIMEOUT_S = 5.0


def test_get_arbitrator_singleton_same_instance():
    """Plusieurs threads obtiennent la même instance (comparaison par is, pas id)."""
    from src.procurement.llm_arbitrator import get_arbitrator, reset_arbitrator

    reset_arbitrator()
    results: list = []
    errors: list[str] = []
    barrier = threading.Barrier(10)

    def worker():
        try:
            barrier.wait(timeout=_BARRIER_TIMEOUT_S)
        except threading.BrokenBarrierError:
            errors.append("barrier broken in singleton test")
            return
        results.append(get_arbitrator())

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=_JOIN_TIMEOUT_S)
        assert not t.is_alive(), "Thread singleton toujours vivant après timeout"

    assert not errors, f"Erreurs barrière : {errors}"
    assert len(results) == 10
    first = results[0]
    assert all(
        r is first for r in results
    ), "Tous les threads doivent obtenir la même instance (is)"


def test_last_cost_thread_local_isolation():
    """Chaque thread voit son propre last_cost, jamais celui d'un autre thread."""
    from src.procurement.llm_arbitrator import get_arbitrator, reset_arbitrator

    reset_arbitrator()
    arb = get_arbitrator()

    thread_costs: dict[str, dict] = {}
    errors: list[str] = []
    barrier_start = threading.Barrier(3)
    barrier_write = threading.Barrier(3)

    def worker(name: str, cost_value: float):
        try:
            barrier_start.wait(timeout=_BARRIER_TIMEOUT_S)
        except threading.BrokenBarrierError:
            errors.append(f"barrier_start broken in {name}")
            return
        arb._tls.last_cost = {"cost_estimate_usd": cost_value}
        try:
            barrier_write.wait(timeout=_BARRIER_TIMEOUT_S)
        except threading.BrokenBarrierError:
            errors.append(f"barrier_write broken in {name}")
            return
        thread_costs[name] = arb.last_cost

    t1 = threading.Thread(target=worker, args=("t1", 0.001))
    t2 = threading.Thread(target=worker, args=("t2", 0.999))
    t3 = threading.Thread(target=worker, args=("t3", 0.500))

    for t in (t1, t2, t3):
        t.start()
    for t in (t1, t2, t3):
        t.join(timeout=_JOIN_TIMEOUT_S)
        assert not t.is_alive(), "Thread last_cost toujours vivant après timeout"

    assert not errors, f"Erreurs barrière : {errors}"
    assert thread_costs["t1"]["cost_estimate_usd"] == 0.001
    assert thread_costs["t2"]["cost_estimate_usd"] == 0.999
    assert thread_costs["t3"]["cost_estimate_usd"] == 0.500


def test_last_cost_default_empty_dict():
    """last_cost retourne {} si jamais écrit dans ce thread."""
    from src.procurement.llm_arbitrator import get_arbitrator, reset_arbitrator

    reset_arbitrator()
    arb = get_arbitrator()

    result: list = []

    def worker():
        result.append(arb.last_cost)

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=_JOIN_TIMEOUT_S)
    assert not t.is_alive(), "Thread default cost toujours vivant après timeout"

    assert result == [{}], "Nouveau thread sans appel doit voir {}"


def test_reset_arbitrator_clears_singleton():
    """reset_arbitrator() force la recréation du singleton."""
    from src.procurement.llm_arbitrator import get_arbitrator, reset_arbitrator

    reset_arbitrator()
    a1 = get_arbitrator()
    reset_arbitrator()
    a2 = get_arbitrator()

    assert a1 is not a2, "Après reset, une nouvelle instance doit être créée"
