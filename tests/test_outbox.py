"""Test outbox pattern — signals only emitted after validation."""
import pytest

from backend.couche_a.models import Case, Lot, Submission, OutboxEvent
from backend.couche_a.outbox import emit_market_signal
from backend.system.db import async_session_factory


@pytest.mark.asyncio
async def test_outbox_only_emits_for_validated():
    """Outbox should only emit for CONF status submissions."""
    async with async_session_factory() as db:
        # Create required Case and Lot for foreign keys
        case = Case(id="C1", reference="C1", title="Test", buyer_name="Tester")
        db.add(case)
        await db.flush()
        lot = Lot(id="L1", case_id="C1", number=1, description="Test lot")
        db.add(lot)
        await db.flush()

        sub = Submission(
            case_id="C1", lot_id="L1", vendor_name="Test",
            status="received", channel="upload"
        )
        db.add(sub)
        await db.flush()

        # Not validated yet
        result = await emit_market_signal(db, sub.id, {"item_name": "test", "unit_price": 100})
        assert result is None

        # Now validate
        sub.status = "CONF"
        await db.flush()

        result = await emit_market_signal(db, sub.id, {"item_name": "test", "unit_price": 100})
        assert result is not None
        assert result.event_type == "market_signal"
        assert result.payload["submission_id"] == sub.id

        await db.commit()
