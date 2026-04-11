"""DMS Settings — V5.2 Pydantic Settings.

Source de vérité unique pour les variables d'environnement.
Fail-fast au démarrage si variable critique manquante.

Les constantes legacy (APP_TITLE, INVARIANTS, paths) sont conservées
pour compatibilité — elles ne dépendent pas de l'environnement.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration centralisée DMS.

    Champs sans default = REQUIRED : absence => ValidationError au démarrage.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- CRITIQUES (required) ---
    DATABASE_URL: str
    # JWT_SECRET est l'alias Railway legacy ; AliasChoices accepte l'un ou l'autre.
    SECRET_KEY: str = Field(
        min_length=32,
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"),
    )
    # Défaut vide : lecture lazy via get_mistral_api_key() → APIKeyMissingError si absent en prod.
    MISTRAL_API_KEY: str = ""

    # --- REDIS ---
    REDIS_URL: str = "redis://localhost:6379"

    # --- TESTING ---
    TESTING: bool = False

    # --- JWT ---
    JWT_ACCESS_TTL_MINUTES: int = Field(default=30, gt=0)
    JWT_REFRESH_TTL_DAYS: int = Field(default=7, gt=0)

    # --- LANGFUSE ---
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    # Si true (hors TESTING) : clés Langfuse obligatoires — sinon échec au premier get_langfuse().
    LANGFUSE_REQUIRED_FOR_LLM: bool = False

    # --- CORS ---
    CORS_ORIGINS: str = ""

    # --- DEPLOYMENT ---
    RUN_MIGRATIONS_ON_STARTUP: bool = False
    RAILWAY_ENVIRONMENT: str = ""
    ENV: str = ""
    DEFAULT_TENANT_CODE: str = "sci_mali"

    # --- OCR / LLM ---
    AZURE_FORM_RECOGNIZER_ENDPOINT: str = ""
    AZURE_FORM_RECOGNIZER_KEY: str = ""
    AZURE_DOC_INTEL_ENDPOINT: str = ""
    AZURE_DOC_INTEL_KEY: str = ""
    LLAMADMS: str = ""
    LLAMA_CLOUD_API_KEY: str = ""
    STORAGE_BASE_PATH: str = ""

    # --- LLM TIER / MODELS ---
    TIER_1_MODEL: str = "mistral-large-latest"
    TIER_1_OCR_MODEL: str = "mistral-ocr-latest"
    ANNOTATION_BACKEND_URL: str = "http://localhost:8001"
    ANNOTATION_TIMEOUT: int = 120

    # --- FEATURE FLAGS ---
    LLM_ARBITRATOR_ENABLED: str = ""
    LLM_ARBITRATOR_MODEL: str = ""

    # Guardrail pré-LLM : 422 si intent RECOMMENDATION (sim ≥ 0,85). Désactivé par défaut
    # (dette technique TD-AGENT-01 — docs/ops/TECHNICAL_DEBT.md).
    AGENT_INV_W06_PRE_LLM_BLOCK: bool = False

    # Accès lecture workspace sans ligne ``workspace_memberships`` / RBAC tenant :
    # JWT legacy (admin, manager, buyer, viewer, auditor) mappé → rôle V5.2 avec
    # ``workspace.read``. DÉFAUT false — activer uniquement pilote / terrain Railway.
    WORKSPACE_ACCESS_JWT_FALLBACK: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "WORKSPACE_ACCESS_JWT_FALLBACK",
            "DMS_WORKSPACE_ACCESS_JWT_FALLBACK",
        ),
    )

    # --- SSL / HTTPX ---
    SSL_CERT_FILE: str = ""
    REQUESTS_CA_BUNDLE: str = ""
    MISTRAL_HTTPX_VERIFY_SSL: str = ""
    MISTRAL_SSL_CA_BUNDLE: str = ""
    LLAMACLOUD_HTTPX_VERIFY_SSL: str = ""

    # --- VENDOR SECURITY ---
    VENDOR_ENCRYPTION_KEY: str = ""
    PSEUDONYM_SALT: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("DATABASE_URL est vide.")
        # Normalise le préfixe SQLAlchemy+psycopg (valide, utilisé localement)
        if v.startswith("postgresql+psycopg://"):
            v = "postgresql://" + v[len("postgresql+psycopg://") :]
        if not (v.startswith("postgresql://") or v.startswith("postgres://")):
            raise ValueError(
                f"DATABASE_URL doit commencer par postgresql:// ou postgres://, "
                f"reçu : {v[:20]}..."
            )
        return v

    @field_validator("LANGFUSE_HOST")
    @classmethod
    def validate_langfuse_host(cls, v: str) -> str:
        v = v.strip()
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"LANGFUSE_HOST doit être une URL HTTP(S), reçu : {v}")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return []
        return [o.strip() for o in raw.split(",") if o.strip()]


# ---------------------------------------------------------------------------
# Legacy constants (ne dépendent pas de l'environnement)
# ---------------------------------------------------------------------------
APP_TITLE = "Decision Memory System — MVP A++ (Production)"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = DATA_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

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


@lru_cache
def get_settings() -> Settings:
    """Singleton cached — une seule instanciation par process.

    lru_cache plutôt que module-level : en pytest, ``get_settings.cache_clear()``
    permet de réinitialiser avec des variables d'env différentes entre tests.
    """
    return Settings()
