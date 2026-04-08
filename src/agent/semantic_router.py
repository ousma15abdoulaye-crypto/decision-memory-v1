"""Semantic Router — Canon V5.1.0 Section 7.3.

Classification d'intent par similarité cosinus avec centroïdes pré-calculés.
5 IntentClass : MARKET_QUERY, WORKSPACE_STATUS, PROCESS_INFO,
                RECOMMENDATION (INV-W06 guardrail), OUT_OF_SCOPE.

INV-A03 : routing sémantique, pas regex.
Seuils : sim >= 0.75 pour classification, >= 0.85 pour RECOMMENDATION.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from src.agent.embedding_client import get_embedding


class IntentClass(StrEnum):
    MARKET_QUERY = "market_query"
    WORKSPACE_STATUS = "workspace_status"
    PROCESS_INFO = "process_info"
    RECOMMENDATION = "recommendation"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass
class IntentResult:
    intent_class: IntentClass
    confidence: float
    matched_centroid: str | None = None


INTENT_EXAMPLES: dict[IntentClass, list[str]] = {
    IntentClass.MARKET_QUERY: [
        "Quel est le prix du ciment à Mopti ?",
        "Prix médian des fournitures scolaires zone Sévaré",
        "Combien coûte le carburant à Bamako ce trimestre ?",
        "Évolution des prix du riz depuis janvier",
        "Comparaison prix entre Mopti et Gao",
        "Quels fournisseurs livrent du matériel médical ?",
        "Tendance prix du gasoil T1 2026",
        "Sources de prix disponibles pour le ciment",
    ],
    IntentClass.WORKSPACE_STATUS: [
        "Où en est le dossier RFQ-2026-041 ?",
        "Combien d'offres reçues pour ce processus ?",
        "Quels fournisseurs ont soumis ?",
        "Le quorum est-il atteint ?",
        "Quel est l'état de la matrice d'évaluation ?",
        "Combien de points signalés restent ouverts ?",
        "Qui fait partie du comité ?",
    ],
    IntentClass.PROCESS_INFO: [
        "Quels sont les seuils ECHO pour les consultations restreintes ?",
        "Quelle est la procédure DGMP pour un DAO ?",
        "Combien de membres minimum pour un comité ?",
        "Quels documents sont éliminatoires ?",
        "Quel est le délai réglementaire pour un appel d'offres ?",
    ],
    IntentClass.RECOMMENDATION: [
        "Quel fournisseur est le meilleur ?",
        "À qui devrait-on attribuer le marché ?",
        "Recommandez-moi un fournisseur",
        "Qui est le moins-disant ?",
        "Classez les fournisseurs du meilleur au pire",
        "Quel est le gagnant ?",
        "Qui devrait remporter le contrat ?",
    ],
}

_centroid_cache: dict[IntentClass, np.ndarray] = {}


async def _ensure_centroids() -> None:
    """Calcule les centroïdes si non en cache."""
    if _centroid_cache:
        return
    for intent_class, examples in INTENT_EXAMPLES.items():
        embeddings = []
        for example in examples:
            emb = await get_embedding(example)
            embeddings.append(emb)
        centroid = np.mean(embeddings, axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        _centroid_cache[intent_class] = centroid


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def classify_intent(query: str) -> IntentResult:
    """Classifie l'intent d'une requête par similarité cosinus (INV-A03).

    Seuils Canon :
    - >= 0.75 : classification standard
    - >= 0.85 : RECOMMENDATION bloqué par guardrail INV-W06
    - < 0.75  : OUT_OF_SCOPE
    """
    await _ensure_centroids()

    query_embedding = await get_embedding(query)
    query_norm = query_embedding / np.linalg.norm(query_embedding)

    best_class = IntentClass.OUT_OF_SCOPE
    best_sim = 0.0

    for intent_class, centroid in _centroid_cache.items():
        sim = _cosine_similarity(query_norm, centroid)
        if sim > best_sim:
            best_sim = sim
            best_class = intent_class

    if best_class == IntentClass.RECOMMENDATION and best_sim >= 0.85:
        return IntentResult(
            intent_class=IntentClass.RECOMMENDATION,
            confidence=best_sim,
        )

    if best_class != IntentClass.RECOMMENDATION and best_sim >= 0.75:
        return IntentResult(
            intent_class=best_class,
            confidence=best_sim,
        )

    return IntentResult(
        intent_class=IntentClass.OUT_OF_SCOPE,
        confidence=best_sim,
    )


def reset_centroid_cache() -> None:
    """Réinitialise le cache de centroïdes (utile pour les tests)."""
    _centroid_cache.clear()
