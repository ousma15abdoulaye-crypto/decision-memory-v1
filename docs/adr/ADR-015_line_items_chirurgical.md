# ADR-015 — Line Items : extraction chirurgicale unités + montants

Date    : 2026-03-16  
Statut  : ACCEPTÉ  
Auteur  : Abdoulaye Ousmane — CTO

## Contexte

Le procurement_dict DMS s'appuie sur les line_items annotés pour alimenter la mémoire marché (market_memory). Sans extraction précise des unités, quantités et prix unitaires, la comparaison inter-offres et le calcul de prix de référence sont impossibles.

Problème identifié 2026-03-16 :
- Le prompt Mistral ne mentionnait pas unit_raw
- Aucun exemple de line_item dans le prompt
- Mistral omettait ou mal-formatait les unités
- Résultat : line_items souvent vides ou incomplets

## Décision

- SCHEMA_VERSION → v3.0.1d
- FRAMEWORK_VERSION → annotation-framework-v3.0.1d
- Prompt Mistral : règle line_items complète + exemples GOODS et SERVICES
- unit_raw obligatoire sur chaque ligne
- line_total_check : OK | ANOMALY | NON_VERIFIABLE
- Si écart > 1% → ambiguites += AMBIG-3

## Périmètre

TOUS les document_role contenant des prix :
- financial_offer → OBLIGATOIRE
- combined_offer → OBLIGATOIRE
- annex_pricing → OBLIGATOIRE
- source_rules → si BOQ/DQE/BPU présent
- tdr_consultance → si budget indicatif (honoraires jour/expert)

RÈGLE ABSOLUE : Toute offre financière = line_items extraits. Lump sum sans tableau = 1 line_item forfait. Jamais line_items = [] si montant visible.

## Unités courantes terrain Mali

GOODS : kg, tonne, litre, pièce, carton, sac, bidon, boîte, palette, m², m³, ml, rouleau, kit, lot  
SERVICES : jour, heure, semaine, mois, forfait, mission, session, rapport, expert-jour  
WORKS : m², m³, ml, unité, poste, ensemble, forfait

## Conséquences

- backend.py mis à jour v3.0.1d
- XML Label Studio inchangé (line_items déjà dans extracted_json)
- procurement_dict peut ingérer les line_items annotés
- Aucune migration Alembic requise
