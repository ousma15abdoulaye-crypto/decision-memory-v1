# UPSTREAM_CONTEXT_PACK_STANDARD

**Version** : `1.0.0`  
**Implémentation** : [`src/annotation/context_pack.py`](../../../src/annotation/context_pack.py)

---

## Objet

Définir le **paquet de contexte amont** injecté avant Pass 1 (et passes spécialisées ultérieures) pour :

- réduire l’hallucination (signaux fournisseur, zone, marché) ;
- aligner l’annotation avec la **mémoire marché** (Couche B) sans violer les frontières Couche A/B en production scoring.

Ce paquet est **lecture seule** : aucune écriture dict / mercuriale depuis le pipeline d’annotation.

---

## Schéma (`UpstreamContextPack`)

| Champ | Type | Source |
| --- | --- | --- |
| `document_id` | `str` | Entrée pipeline |
| `case_id` | `str \| null` | DB `documents.case_id` si résolu |
| `vendor_catalog_summary` | `dict` | Ex. `active_vendor_count`, `sample_zones` — agrégats anonymisés |
| `mercuriale_summary` | `dict` | Ex. `mercurial_row_count`, `latest_year` |
| `market_signal_hint` | `dict \| null` | Résumé non prescriptif (pas de `winner` / `rank`) |
| `procurement_hints` | `list[str]` | Chaînes sûres (pas de PII) |
| `pack_version` | `str` | SemVer du format du pack |
| `sources_used` | `list[str]` | Traçabilité : `vendors`, `mercurials`, `none`, … |

---

## Règles

1. **Pas de PII** dans le pack par défaut (noms fournisseurs bruts interdits sauf mandat sécurité).
2. **Dégradation gracieuse** : si DB indisponible → pack vide avec `sources_used: ["none"]`.
3. **Tests CI** : pas de connexion DB réelle — mocks / `skip_if_no_database`.

---

## Évolution

Les champs additionnels passent par révision de ce document + bump `pack_version`.
