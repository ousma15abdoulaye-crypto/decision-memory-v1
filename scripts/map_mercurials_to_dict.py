#!/usr/bin/env python3
"""
scripts/map_mercurials_to_dict.py

Résout mercurials.item_canonical
→ procurement_dict_items.item_id

Stratégie :
  1. Normaliser les deux textes
  2. Similarity bigram sur texte normalisé
  3. Seuil 0.45 (textes bruités)
  4. Garder meilleur match par item_canonical
  5. Produire CSV de propositions pour validation AO
  6. Mode --apply pour UPDATE après validation

Usage :
  python scripts/map_mercurials_to_dict.py --propose
  python scripts/map_mercurials_to_dict.py --apply \
    --validated mercurials_mapping_proposals.csv
"""

import os
import sys
import re
import csv
import argparse

import psycopg
from psycopg.rows import dict_row

try:
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

SEUIL_AUTO = 0.72  # confiance haute -> appliquer
SEUIL_REVUE = 0.45  # confiance moyenne -> révision AO
OUTPUT_CSV = "mercurials_mapping_proposals.csv"


def normalize(text: str) -> str:
    """Normalisation agressive pour texte PDF bruité."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"[^a-zàâäéèêëîïôùûüç\s]", " ", t)
    stopwords = {
        "de", "du", "des", "le", "la", "les", "un", "une",
        "et", "en", "au", "aux", "par", "pour", "sur", "avec",
        "dans", "ce", "se", "sa", "son", "ses", "ou", "que",
        "qui", "lot", "kit", "sac", "boite", "bidon",
        "bouteille", "litre", "kg", "ml", "cm", "mm",
        "piece", "unite", "forfait", "abonnement",
    }
    tokens = [w for w in t.split() if w not in stopwords and len(w) > 2]
    return " ".join(tokens)


def _bigram_similarity(a: str, b: str) -> float:
    """Similarity bigram Jaccard entre deux strings."""

    def bigrams(s: str) -> set:
        s = f"  {s}  "
        return {s[i : i + 2] for i in range(len(s) - 1)}

    if not a or not b:
        return 0.0
    ba = bigrams(a)
    bb = bigrams(b)
    inter = len(ba & bb)
    union = len(ba | bb)
    return inter / union if union > 0 else 0.0


def env() -> str:
    # Priorité : RAILWAY_DATABASE_URL pour opérations Railway
    u = os.environ.get("RAILWAY_DATABASE_URL", "")
    if not u:
        u = os.environ.get("DATABASE_URL", "")
    if not u:
        raise SystemExit("DATABASE_URL / RAILWAY_DATABASE_URL absente")
    return u.replace("postgresql+psycopg://", "postgresql://")


def run_propose(db_url: str) -> None:
    conn = psycopg.connect(db_url, row_factory=dict_row)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT item_canonical,
               COUNT(*) AS nb_lignes,
               AVG(price_avg) AS prix_moyen,
               MIN(year) AS annee_min,
               MAX(year) AS annee_max
        FROM mercurials
        WHERE item_canonical IS NOT NULL
          AND item_id IS NULL
        GROUP BY item_canonical
        ORDER BY COUNT(*) DESC
    """)
    canonicals = cur.fetchall()
    print(f"item_canonical a mapper : {len(canonicals)}")

    cur.execute("""
        SELECT item_id, label_fr, item_code, taxo_l1, taxo_l3
        FROM couche_b.procurement_dict_items
        WHERE active = TRUE
    """)
    dict_items = cur.fetchall()
    print(f"Items dictionnaire : {len(dict_items)}")

    dict_normalized = [
        {
            "item_id": d["item_id"],
            "label_fr": d["label_fr"],
            "item_code": d["item_code"],
            "taxo_l1": d["taxo_l1"],
            "taxo_l3": d["taxo_l3"],
            "normalized": normalize(d["label_fr"]),
        }
        for d in dict_items
        if normalize(d["label_fr"])
    ]

    proposals = []
    no_match = []

    for i, row in enumerate(canonicals):
        canonical = row["item_canonical"]
        canonical_norm = normalize(canonical)

        if not canonical_norm:
            no_match.append(canonical)
            continue

        best_score = 0.0
        best_item = None

        for d in dict_normalized:
            if not d["normalized"]:
                continue
            score = _bigram_similarity(canonical_norm, d["normalized"])
            if score > best_score:
                best_score = score
                best_item = d

        if best_item and best_score >= SEUIL_REVUE:
            proposals.append(
                {
                    "item_canonical": canonical,
                    "canonical_norm": canonical_norm,
                    "item_id_propose": best_item["item_id"],
                    "label_fr_propose": best_item["label_fr"],
                    "item_code": best_item["item_code"],
                    "taxo_l1": best_item["taxo_l1"],
                    "taxo_l3": best_item["taxo_l3"],
                    "score": round(best_score, 3),
                    "confiance": (
                        "AUTO" if best_score >= SEUIL_AUTO else "REVUE"
                    ),
                    "nb_lignes": row["nb_lignes"],
                    "prix_moyen": float(row["prix_moyen"] or 0),
                    "annees": f"{row['annee_min']}-{row['annee_max']}",
                    "valider_oui_non": (
                        "OUI" if best_score >= SEUIL_AUTO else ""
                    ),
                }
            )
        else:
            no_match.append(canonical)

        if i % 200 == 0:
            print(f"  {i}/{len(canonicals)} traites...")

    proposals.sort(key=lambda x: x["score"], reverse=True)

    if proposals:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(proposals[0].keys()))
            writer.writeheader()
            writer.writerows(proposals)

    auto = sum(1 for p in proposals if p["confiance"] == "AUTO")
    revue = sum(1 for p in proposals if p["confiance"] == "REVUE")

    print(f"\n{'='*55}")
    print(f"RESULTATS MAPPING MERCURIALS")
    print(f"{'='*55}")
    print(f"  Traites      : {len(canonicals)}")
    print(f"  Avec match   : {len(proposals)}")
    print(f"  AUTO (>={SEUIL_AUTO:.0%})  : {auto}")
    print(f"  REVUE        : {revue}")
    print(f"  Sans match   : {len(no_match)}")
    print(f"\n  CSV          : {OUTPUT_CSV}")

    if proposals:
        print(f"\n  Top 15 AUTO (score >= {SEUIL_AUTO}) :")
        shown = [p for p in proposals if p["confiance"] == "AUTO"][:15]
        for p in shown:
            print(
                f"    {p['score']:.3f} | "
                f"{p['item_canonical'][:35]:35s} -> "
                f"{p['label_fr_propose'][:35]}"
            )

    if no_match:
        print(f"\n  Top 10 sans match :")
        for c in no_match[:10]:
            print(f"    {c[:60]}")

    conn.close()


def run_apply(db_url: str, csv_path: str) -> None:
    """Applique le mapping validé. UPDATE mercurials.item_id."""
    conn = psycopg.connect(db_url, row_factory=dict_row)
    cur = conn.cursor()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    valides = [r for r in rows if r.get("valider_oui_non", "").upper() == "OUI"]
    print(f"Mappings a appliquer : {len(valides)}")

    ok = err = 0
    for r in valides:
        try:
            cur.execute(
                """
                UPDATE mercurials
                SET item_id = %s
                WHERE item_canonical = %s
                  AND item_id IS NULL
                """,
                (r["item_id_propose"], r["item_canonical"]),
            )
            updated = cur.rowcount
            ok += updated
            if updated > 0:
                print(
                    f"  OK {updated:4d} | "
                    f"{r['item_canonical'][:40]:40s} -> "
                    f"{r['label_fr_propose'][:30]}"
                )
        except Exception as e:
            print(f"  ERR {r['item_canonical'][:40]}: {e}")
            err += 1

    conn.commit()
    print(f"\nRESULTAT : ok={ok} err={err}")

    cur.execute("""
        SELECT COUNT(*) AS total,
               COUNT(item_id) AS avec_item_id,
               COUNT(*) - COUNT(item_id) AS sans_item_id
        FROM mercurials
    """)
    r = cur.fetchone()
    pct = r["avec_item_id"] / r["total"] * 100 if r["total"] > 0 else 0
    print(f"\nEtat mercurials apres mapping :")
    print(f"  Total        : {r['total']}")
    print(f"  Avec item_id : {r['avec_item_id']}")
    print(f"  Sans item_id : {r['sans_item_id']}")
    print(f"  Couverture   : {pct:.1f}%")
    conn.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--propose", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--validated", default=OUTPUT_CSV)
    args = p.parse_args()

    db = env()

    if args.propose:
        run_propose(db)
    elif args.apply:
        run_apply(db, args.validated)
    else:
        print("Usage : --propose ou --apply")
        sys.exit(1)


if __name__ == "__main__":
    main()
