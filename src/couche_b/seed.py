"""
Couche B — Seed Data Mali
Constitution DMS V2.1 §4.4 (Geo) + §4.3 (Units)
"""

from sqlalchemy import text
from src.db import engine

# TODO Session 2.2: Implémenter seed

async def seed_couche_b():
    """
    Seed Couche B with Mali standard data:
    - 8 geo zones (Bamako, Gao, Tombouctou, Mopti, Sikasso, Ségou, Kayes, Koulikoro)
    - 9 standard units (kg, tonne, L, m³, m, m², pièce, sac, carton)
    - 3 common vendors (SOGELEC, SOMAPEP, COVEC)
    - 5 common items (Ciment, Fer 12mm, Riz, Huile, Sucre)
    """
    async with engine.begin() as conn:
        # TODO: INSERT geo_master
        # TODO: INSERT geo_aliases
        # TODO: INSERT units
        # TODO: INSERT unit_aliases
        # TODO: INSERT vendors
        # TODO: INSERT items
        pass

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_couche_b())
    print("✅ Couche B seeded")
