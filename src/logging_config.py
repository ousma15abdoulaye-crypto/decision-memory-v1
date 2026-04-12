"""Configuration logging pour resilience patterns."""

import logging
import sys


def configure_logging():
    """Configure logging avec niveau détail."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("dms.log")],
    )

    # Niveau DEBUG pour resilience
    logging.getLogger("src.resilience").setLevel(logging.DEBUG)
    logging.getLogger("tenacity").setLevel(logging.INFO)

    # Mistral SDK / httpx : chaque embedding loggait une ligne INFO (inondation Railway).
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
