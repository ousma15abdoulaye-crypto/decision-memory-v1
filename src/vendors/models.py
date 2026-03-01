"""
Modèles Pydantic pour vendor_identities — M4.
Lecture seule · pas de création via API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class VendorOut(BaseModel):
    id: UUID
    vendor_id: str
    name_raw: str
    name_normalized: str
    zone_raw: str | None
    zone_normalized: str | None
    region_code: str
    category_raw: str | None
    email: str | None
    phone: str | None
    email_verified: bool
    is_active: bool
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
