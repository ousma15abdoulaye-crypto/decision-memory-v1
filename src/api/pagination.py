"""Pagination standard pour routes liste (F5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PaginationParams:
    page: int = 1
    page_size: int = 50

    def __post_init__(self) -> None:
        if self.page < 1:
            self.page = 1
        if self.page_size < 1:
            self.page_size = 1
        if self.page_size > 200:
            self.page_size = 200

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def paginated_response(
    *,
    items: list[Any],
    total: int,
    params: PaginationParams,
    key: str = "items",
) -> dict[str, Any]:
    ps = params.page_size
    total_pages = max(1, (total + ps - 1) // ps) if total > 0 else 1
    return {
        key: items,
        "pagination": {
            "page": params.page,
            "page_size": params.page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": params.page * params.page_size < total,
            "has_previous": params.page > 1,
        },
    }
