# MERCURIALE_COLUMN_MAP.md

## Source
Mercuriales officielles Mali · DGMP · Ministère du Commerce
Années ingérées Phase 1 : 2024 (d'abord) · 2023 (ensuite)

---

## Structure fichiers Phase 1

| Année | Fichier(s) | Structure |
|---|---|---|
| 2024 | `Mercuriale des prix 2024 ( Combiné de Toutes les regions ).pdf` | 1 fichier · bloc par zone · en-tête "Prix TTC, Zone, 2024" |
| 2023 | `Mercuriale des prix 2023/Bulletin_Result_[Zone]2023.pdf` (16 fichiers) | 1 fichier par zone · zone extraite du nom de fichier |

## Ordre d'import Phase 1

2024 en premier : structure bloc par zone · plus simple · calibre le parser
2023 en second  : 16 fichiers séparés · zone dans le nom de fichier · plus dense

---

## Structure PDF confirmée (probe visuel CTO)

| Élément | Format | Exemple |
|---|---|---|
| En-tête zone | `Prix TTC, <Zone>, <Année>` | `Prix TTC, Kayes, 2024` |
| Groupe | `N. Libellé groupe` (bold Markdown) | `**1. Fournitures de bureau**` |
| Article | code · désignation · unité · prix min · moy · max | `\| 1.3 \| Abonnement... \| Annuel \| 70 000 \| 77 500 \| 85 000 \|` |

---

## Colonnes PDF → Champs DB

| Colonne PDF | Champ DB | Type | Notes |
|---|---|---|---|
| Code | `item_code` | TEXT | ex : `"1.3"` |
| DESIGNATIONS | `item_canonical` | TEXT NOT NULL | libellé brut · jamais normalisé |
| Unité | `unit_raw` | TEXT | ex : `"Paquet 10"` |
| Prix Min | `price_min` | NUMERIC(15,4) | plancher officiel |
| Prix Moyen | `price_avg` | NUMERIC(15,4) | référence marché = unit_price |
| Prix Max | `price_max` | NUMERIC(15,4) | plafond officiel |
| Zone (en-tête ou nom fichier) | `zone_raw` | TEXT | ex : `"Kayes"` |
| Groupe (section) | `group_label` | TEXT | ex : `"Fournitures de bureau"` |
| Année (titre ou nom fichier) | `year` | INTEGER | 2024 · 2023 |

---

## Devise
XOF (Franc CFA BCEAO) · hard-codé · pas de colonne PDF

---

## Invariant prix
`price_min ≤ price_avg ≤ price_max`
Si violation → `review_required = True` + flag `extraction_metadata`
Pas de CHECK DB en M5 (ingestion brute · RÈGLE-29)

---

## Seuils confidence

| Seuil | Action |
|---|---|
| ≥ 0.80 | Insertion normale |
| 0.60 → 0.79 | Insertion + `review_required = True` |
| < 0.60 | Rejetée · comptée `skipped_low_confidence` |

---

## Résolution zone_raw → geo_master.id

Algorithme (dans `repository.py::resolve_zone_id`) :
1. Exact match ILIKE `zone_raw` → LIMIT 2 (détecter ambiguïtés)
2. Si 0 résultat : contains match ILIKE `%zone_raw%` → LIMIT 2
3. Si 1 résultat unique → `zone_id` résolu
4. Si 0 ou > 1 résultat → `zone_id = NULL` · `zone_raw` conservé · flag metadata

Pour 2023 : `zone_raw` extrait du nom de fichier via `_zone_from_filename()`.
`geo_master` enrichi en M5-GEO-FIX : 17 zones · 16/16 couverts.

---

## Mapping nom fichier → zone_raw (2023)

| Clé dans nom fichier | zone_raw canonical |
|---|---|
| `bko` | Bamako |
| `bougouni` | Bougouni |
| `dioila` | Dioïla |
| `gao` | Gao |
| `kidal` | Kidal |
| `kita` | Kita |
| `koulikoro` | Koulikoro |
| `menaka` | Ménaka |
| `mopti` | Mopti |
| `nara` | Nara |
| `nioro` | Nioro |
| `san` | San |
| `segou` | Ségou |
| `sikasso` | Sikasso |
| `taoudeni` | Taoudeni |
| `tombouctou` | Tombouctou |
