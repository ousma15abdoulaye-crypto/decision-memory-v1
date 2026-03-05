"""Test rapide du parser sur le fichier cache Bougouni."""
from pathlib import Path
from src.couche_b.mercuriale.ingest_parser import parse_html_to_lines

md = Path("data/imports/m5/cache/sample_probe_bougouni.md").read_text(encoding="utf-8")
lines = parse_html_to_lines(md, 2023, default_zone_raw="Bougouni")
print(f"Lignes extraites : {len(lines)}")
for ln in lines[:5]:
    print(
        f"  {ln['item_code']} | {ln['item_canonical'][:40]:<40} | "
        f"min={ln['price_min']} moy={ln['price_avg']} max={ln['price_max']} | "
        f"zone={ln['zone_raw']}"
    )
if lines:
    print(f"\nPremier group_label : {lines[0]['group_label']}")
    print(f"Coverage : {len(lines)} lignes valides")
