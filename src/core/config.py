"""
Configuration settings for Decision Memory System.
Constitution V2.1: ONLINE-ONLY (PostgreSQL).
"""
from pathlib import Path

# =========================================================
# Decision Memory System — MVP A++ FINAL
# Version: 1.0.0
# DAO-driven extraction + Template-adaptive CBA + Active Memory
# Constitution V2.1: ONLINE-ONLY (PostgreSQL)
# =========================================================

APP_TITLE = "Decision Memory System — MVP A++ (Production)"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = DATA_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)


# =========================
# CONSTITUTION (V2.1 ONLINE-ONLY)
# =========================
INVARIANTS = {
    "cognitive_load_never_increase": True,
    "human_decision_final": True,
    "no_scoring_no_ranking_no_recommendations": True,
    "memory_is_byproduct_never_a_task": True,
    "erp_agnostic": True,
    "online_only": True,
    "traceability_keep_sources": True,
    "one_dao_one_cba_one_pv": True,
}
