# Statut public des réponses HTTP 501

**Décision produit** : ces endpoints restent **dans le graphe OpenAPI** pour traçabilité et clients internes ; ils ne sont pas des « oublis » à corriger en hotfix sans mandat métier.

| Méthode | Chemin (prefix inclus) | Comportement | Référence code |
|---------|-------------------------|--------------|----------------|
| POST | `/api/scoring/calculate` | 501 — scoring uniquement via pipeline FSM (atomicité, garde-fous). | `src/couche_a/scoring/api.py` |
| POST | `/api/analyze` | Peut renvoyer 501 tant que l’extraction structurée des critères DAO n’est pas branchée (étape 1). | `src/api/analysis.py` (`extract_dao_criteria_structured`) |

**Alternatives CTO** (non retenues dans ce plan) : retirer les routes du schéma public, ou les masquer derrière un feature flag. Toute évolution passe par ADR et mandat.

Voir aussi la description OpenAPI sur l’instance `main:app` (`main.py`).
