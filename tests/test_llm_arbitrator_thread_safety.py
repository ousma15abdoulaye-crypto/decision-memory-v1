"""
Tests thread-safety LLMArbitrator.

T1 : get_arbitrator() retourne la même instance depuis plusieurs threads
     (singleton, double-checked locking).
T2 : _tls.last_cost est isolé par thread — un thread ne voit pas le coût
     du thread voisin.
T3 : reset_arbitrator() réinitialise proprement le singleton.
"""

from __future__ import annotations

import threading


def test_get_arbitrator_singleton_same_instance():
    """Plusieurs threads obtiennent la même instance."""
    from src.procurement.llm_arbitrator import get_arbitrator, reset_arbitrator

    reset_arbitrator()
    results: list = []
    barrier = threading.Barrier(10)

    def worker():
        barrier.wait()
        results.append(id(get_arbitrator()))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(results)) == 1, "Tous les threads doivent obtenir le même singleton"


def test_last_cost_thread_local_isolation():
    """Chaque thread voit son propre last_cost, jamais celui d'un autre thread."""
    from src.procurement.llm_arbitrator import get_arbitrator, reset_arbitrator

    reset_arbitrator()
    arb = get_arbitrator()

    thread_costs: dict[str, dict] = {}
    barrier = threading.Barrier(3)

    def worker(name: str, cost_value: float):
        barrier.wait()
        arb._tls.last_cost = {"cost_estimate_usd": cost_value}
        barrier.wait()
        thread_costs[name] = arb.last_cost

    t1 = threading.Thread(target=worker, args=("t1", 0.001))
    t2 = threading.Thread(target=worker, args=("t2", 0.999))
    t3 = threading.Thread(target=worker, args=("t3", 0.500))

    for t in (t1, t2, t3):
        t.start()
    for t in (t1, t2, t3):
        t.join()

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
    t.join()

    assert result == [{}], "Nouveau thread sans appel doit voir {}"


def test_reset_arbitrator_clears_singleton():
    """reset_arbitrator() force la recréation du singleton."""
    from src.procurement.llm_arbitrator import get_arbitrator, reset_arbitrator

    reset_arbitrator()
    a1 = get_arbitrator()
    reset_arbitrator()
    a2 = get_arbitrator()

    assert a1 is not a2, "Après reset, une nouvelle instance doit être créée"
