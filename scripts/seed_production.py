#!/usr/bin/env python3
"""
Seed production database with Couche B data
Usage: python scripts/seed_production.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.couche_b.seed import seed_couche_b

if __name__ == "__main__":
    print("🌱 Seeding Couche B...")
    asyncio.run(seed_couche_b())
    print("✅ Done")
