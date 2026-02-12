"""
Extraction documentaire – Stubs synchrones pour background tasks.
Milestone 3 – implémentation réelle.
"""
import time
from pathlib import Path


def extract_dao_content(case_id: str, artifact_id: str, filepath: str):
    """
    Extraction (synchrone) des critères techniques depuis le DAO.
    """
    time.sleep(2)
    print(f"Extraction DAO terminée pour case {case_id}, artifact {artifact_id}")
    return {"status": "completed"}


def extract_offer_content(
    case_id: str, artifact_id: str, filepath: str, offer_type: str
):
    """
    Extraction (synchrone) selon le type d'offre.
    """
    time.sleep(2)
    print(f"Extraction offre {offer_type} terminée pour case {case_id}, artifact {artifact_id}")
    return {"status": "completed"}
