"""
Couche B — SQLAlchemy Models
Constitution DMS V2.1 §4 (Catalogs) + §5 (Market Signals)
"""

from sqlalchemy import (
    Table, Column, String, Integer, Float, Date, TIMESTAMP,
    ForeignKey, Index, CheckConstraint, UniqueConstraint,
    Text, ARRAY, JSON
)
from sqlalchemy.sql import func
from src.db import metadata

# TODO Session 1.2: Implémenter 9 tables
# 1. vendors
# 2. vendor_aliases
# 3. vendor_events
# 4. items
# 5. item_aliases
# 6. units
# 7. unit_aliases
# 8. geo_master
# 9. geo_aliases
# 10. market_signals

# RÉFÉRENCE: Constitution V2.1 §4.2, §4.3, §4.4, §5.1
