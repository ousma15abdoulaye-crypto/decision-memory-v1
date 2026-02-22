from enum import StrEnum

from pydantic import BaseModel


class NormStrategy(StrEnum):
    EXACT_ALIAS_RAW = "exact_alias_raw"
    EXACT_NORMALIZED_ALIAS = "exact_normalized_alias"
    UNRESOLVED = "unresolved"


class NormalisationResult(BaseModel):
    input_raw: str
    normalized_input: str
    item_id: str | None
    strategy: NormStrategy
    score: float  # 1.0 exact / 0.0 unresolved
    confidence_note: str | None = None

    model_config = {"use_enum_values": True}
