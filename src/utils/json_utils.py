"""JSON helpers — sérialisation sûre pour snapshots et journaux (UUID, datetime)."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from typing import Any


def _default_serializer(obj: object) -> str:
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def safe_json_dumps(data: dict[str, Any], **kwargs: Any) -> str:
    """json.dumps avec sérialisation UUID et datetime (y compris valeurs imbriquées).

    Ne pas passer ``default=`` : réservé au sérialiseur interne.
    """
    if "default" in kwargs:
        raise ValueError(
            "safe_json_dumps: ne pas passer 'default'; UUID/datetime gérés en interne."
        )
    return json.dumps(data, default=_default_serializer, **kwargs)
