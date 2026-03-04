"""Probe : vérifie le mapping zone des 18 fichiers 2026."""
import sys
sys.path.insert(0, ".")

from scripts.import_mercuriale import build_files_year
from pathlib import Path

folder = Path("data/imports/m5/Mercuriale des prix 2026")
files = build_files_year(folder, 2026)
print(f"Fichiers detectes : {len(files)}\n")
ok = 0
ko = 0
for f in files:
    zone = f["default_zone_raw"] or "ZONE MANQUANTE"
    status = "OK" if f["default_zone_raw"] else "KO"
    if status == "OK":
        ok += 1
    else:
        ko += 1
    print(f"  {status} | {zone:<22} | {f['path'].name}")

print(f"\nTotal : {ok} OK · {ko} sans zone")
