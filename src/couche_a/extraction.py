"""
Extraction documentaire – Stubs pour background tasks.
Seront complétés dans Milestone 3.
"""
from __future__ import annotations

import asyncio
from pathlib import Path


async def extract_dao_content(case_id: str, artifact_id: str, filepath: str):
    """
    Extraction async des critères techniques depuis le DAO.
    (Milestone 3 – implémentation réelle)
    """
    # Simuler un travail long
    await asyncio.sleep(2)
    print(f"Extraction DAO terminée pour case {case_id}, artifact {artifact_id}")
    # Ici : mise à jour de l'artifact avec les données extraites
    return {"status": "completed"}


async def extract_offer_content(
    case_id: str, artifact_id: str, filepath: str, offer_type: str
):
    """
    Extraction async des données selon le type d'offre.
    (Milestone 3 – implémentation réelle)
    """
    await asyncio.sleep(2)
    print(f"Extraction offre {offer_type} terminée pour case {case_id}, artifact {artifact_id}")
    return {"status": "completed"}
