"""P3.3 — trace structurée minimale (stdlib logging, sans dépendance)."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger("dms.p33")


def log_p33_structured(event: str, **fields: object) -> None:
    """Émet une ligne JSON pour support / lecture opérationnelle."""
    payload: dict[str, object] = {"p33_event": event, **fields}
    logger.info("p33 %s", json.dumps(payload, ensure_ascii=False, default=str))


__all__ = ["log_p33_structured"]
