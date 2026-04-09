# Load .env and .env.local before db import (DATABASE_URL required)
try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

# Configure logging pour resilience patterns
from src.logging_config import configure_logging

configure_logging()

from src.api.app_factory import create_railway_app
from src.core.models import (
    AnalyzeRequest,
    CaseCreate,
    DecideRequest,
)

app = create_railway_app()

# Rebuild Pydantic models to resolve forward references
try:
    CaseCreate.model_rebuild()
    AnalyzeRequest.model_rebuild()
    DecideRequest.model_rebuild()
except Exception:
    pass  # Ignore if models don't need rebuilding

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
