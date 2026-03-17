# RAPPORT DE DÉFAILLANCE — M7.4 PHASE A

**Date :** 2026-03-07  
**Sévérité :** CRITIQUE  
**Statut :** TRAVAIL BÂCLÉ — À REPRENDRE  
**Référence :** `scripts/classify_taxonomy_v2.py` · `scripts/seed_taxonomy_v2.py`

---

## 1. RÉSUMÉ EXÉCUTIF

La Phase A (classification taxonomique L1/L2/L3 par LLM Mistral) a échoué avec un taux de **77,9 %** de propositions flaggées, au lieu d’un seuil cible de 35 % maximum (STOP-V3). La cause principale : **le LLM invente des codes L3** absents de la taxonomie, alors que le prompt impose explicitement la liste des codes valides.

**Conséquence :** Le pipeline est inutilisable en l’état. Les 834 propositions flaggées nécessitent une revue manuelle ou une refonte complète du dispositif.

---

## 2. ÉTAT DES LIEUX

| Métrique | Valeur | Attendue |
|----------|--------|----------|
| Proposals total | 1070 | 1484 |
| pending | 236 | 70%+ |
| flagged | 834 | ≤ 35% |
| flagged_pct | **77,9 %** | ≤ 35 % |
| residuel_pct | **77,9 %** | ≤ 25 % |
| Gates STOP-V3 / STOP-V4 | **DÉPASSÉS** | OK |

---

## 3. CAUSE RACINE — INVENTION DE CODES L3 PAR LE LLM

### 3.1 Mécanisme

Le prompt contient **tous les codes L3 valides** (23 codes) :

```
NIVEAU L3 (codes valides) :
4x4 | abonnements_presse | antibiotiques | antipaludiques | camions | ciment | chaux | csp | DIVERS_NON_CLASSE | essence | gasoil | gilets | imprimantes | legumineuses | mais | masques_gants | mil_sorgho | ordinateurs | petrole | platre | plumpy_nut | riz | vitamines
```

Le LLM **ne respecte pas** cette contrainte. Pour des articles sans correspondance exacte dans L3, il :

1. Génère un code **sémantiquement plausible** (ex. `cafe` pour « Café Maxwell »)
2. Ignore la règle « Si incertain → DIVERS_NON_CLASSE »
3. Produit des codes **inventés** qui n’existent pas en base

### 3.2 Inventaire des codes L3 inventés (observés dans les logs)

| Code inventé | Domaine | Exemple article | Code L3 valide attendu |
|--------------|---------|-----------------|-------------------------|
| `cafe` | ALIM_VIVRES | Café Maxwell, Café moulu | — (aucun) → DIVERS_NON_CLASSE |
| `lait` | ALIM_VIVRES | Lait Nido, Lait Président | — (aucun) → DIVERS_NON_CLASSE |
| `farine` | ALIM_VIVRES | Farine 50 kg | legumineuses ? → DIVERS_NON_CLASSE |
| `fromage` | ALIM_VIVRES | Fromage | — (aucun) → DIVERS_NON_CLASSE |
| `aubergine` | ALIM_VIVRES | Aubergine | — (aucun) → DIVERS_NON_CLASSE |
| `assiettes_*` | ALIM_VIVRES | Assiettes Duralex, plastique | — (aucun) → DIVERS_NON_CLASSE |
| `bois` | TRAVAUXCONST | Bois brut, Bois rouge | — (aucun) → DIVERS_NON_CLASSE |
| `fer` | TRAVAUXCONST | Fer à béton, Fer rond | — (aucun) → DIVERS_NON_CLASSE |
| `fer_beton` | TRAVAUXCONST | Fer à béton | — (aucun) → DIVERS_NON_CLASSE |
| `fer_carre_06` | TRAVAUXCONST | Barreau fer | — (aucun) → DIVERS_NON_CLASSE |
| `fer_ha_*` | TRAVAUXCONST | Fer HA 8, 10, 12 | — (aucun) → DIVERS_NON_CLASSE |
| `ardoise` | TRAVAUXCONST | Ardoise | — (aucun) → DIVERS_NON_CLASSE |
| `ardoisine` | TRAVAUXCONST | Ardoisine | — (aucun) → DIVERS_NON_CLASSE |
| `argile` | TRAVAUXCONST | Argile | — (aucun) → DIVERS_NON_CLASSE |
| `ballast` | TRAVAUXCONST | Ballast | — (aucun) → DIVERS_NON_CLASSE |
| `gravier` | TRAVAUXCONST | Gravier | — (aucun) → DIVERS_NON_CLASSE |
| `gravillon` | TRAVAUXCONST | Gravillon 0/4, 4/6 | — (aucun) → DIVERS_NON_CLASSE |
| `gravier_15_25` | TRAVAUXCONST | Gravier 15/25 | — (aucun) → DIVERS_NON_CLASSE |
| `laterites` | TRAVAUXCONST | Latérites | — (aucun) → DIVERS_NON_CLASSE |
| `peinture` | TRAVAUXCONST | Peinture | — (aucun) → DIVERS_NON_CLASSE |
| `barreau_acier_*` | TRAVAUXCONST | Barreau acier | — (aucun) → DIVERS_NON_CLASSE |
| `pelottes_cordeaux_*` | TRAVAUXCONST | Pelottes cordeau | — (aucun) → DIVERS_NON_CLASSE |
| `bazin` | VETEMENT | Bazin riche, Bazin java | — (aucun) → DIVERS_NON_CLASSE |
| `motos` | VEHICUL | Moto Honda CG125 | — (aucun) → DIVERS_NON_CLASSE |
| `pelle_mecanique` | VEHICUL | Pelle mécanique | — (aucun) → DIVERS_NON_CLASSE |
| `pelle_pneus` | VEHICUL | Pelle sur pneus | — (aucun) → DIVERS_NON_CLASSE |
| `pelle_mecanique_hydraulique` | VEHICUL | Pelle hydraulique | — (aucun) → DIVERS_NON_CLASSE |

### 3.3 Couverture de la taxonomie L3 actuelle

La taxonomie L3 contient **23 codes** couvrant :

- **Céréales** : riz, mil_sorgho, mais, legumineuses  
- **Matériaux liants** : ciment, chaux, platre  
- **Carburants** : gasoil, essence, petrole  
- **Médicaments** : antibiotiques, antipaludiques, vitamines  
- **Nutrition thérapeutique** : plumpy_nut, csp  
- **IT** : ordinateurs, imprimantes  
- **Véhicules** : 4x4, camions  
- **EPI** : masques_gants, gilets  
- **Médias** : abonnements_presse  
- **Résiduel** : DIVERS_NON_CLASSE  

**Manques** : café, lait, farine, fromage, bois, fer, gravier, peinture, bazin, motos, etc. — soit environ 40 % du catalogue terrain.

---

## 4. DÉFAUTS DE CONCEPTION

### 4.1 Prompt insuffisant

- Le prompt liste les codes L3 mais ne les impose pas comme **contrainte stricte**.
- Aucune instruction du type : « Si aucun code ne correspond exactement → DIVERS_NON_CLASSE. Ne jamais inventer de code. »
- Le LLM privilégie une réponse sémantique plutôt que le respect strict de la liste.

### 4.2 Taxonomie L3 limitée

- La taxonomie L3 a été conçue sans analyse préalable du catalogue terrain.
- 23 codes pour ~1484 items → couverture insuffisante pour des produits courants (café, lait, farine, bois, fer, bazin, etc.).

### 4.3 Perte d’information en cas d’erreur

- Le `reason` stocké en base est tronqué à 40 caractères : `f"pydantic:{str(e)[:40]}"`.
- Les codes invalides ne sont pas conservés pour analyse.
- Aucune métrique dédiée sur les codes inventés.

### 4.4 Absence de validation pré-LLM

- Aucune vérification que le catalogue terrain est couvert par la taxonomie avant le run.
- Pas de mapping « article → code L3 valide le plus proche » pour les cas ambigus.

---

## 5. ACTIONS CORRECTIVES REQUISES

### 5.1 Court terme (blocage)

1. **Arrêter le full run** en cours et ne plus lancer de Phase A sans correction.
2. **Renforcer le prompt** :
   - « Si aucun code L3 ne correspond exactement à l’article, utiliser UNIQUEMENT DIVERS_NON_CLASSE. Ne jamais inventer de code. »
   - Option : « Répondre uniquement avec un code parmi : [liste exhaustive]. »
3. **Validation post-LLM** : si `subfamily_id` ∉ `valid_l3`, remplacer automatiquement par `DIVERS_NON_CLASSE` (sans flag).

### 5.2 Moyen terme (qualité)

1. **Enrichir la taxonomie L3** en analysant le catalogue terrain :
   - Extraire les items les plus fréquents et les regrouper.
   - Ajouter les codes manquants : cafe, lait, farine, bois, fer_a_beton, gravier, peinture, bazin, motos, etc.
2. **Analyse de couverture** : script avant Phase A pour mesurer le % d’items couverts par L3.
3. **Stocker le code LLM brut** : colonne `llm_subfamily_id_raw` pour tracer les inventions.

### 5.3 Long terme (robustesse)

1. **Structured output** : utiliser l’API Mistral pour des réponses contraintes (enum) si disponible.
2. **Two-stage** : classification L1/L2 d’abord, puis L3 uniquement si mapping possible.
3. **Fallback** : si L3 inventé → DIVERS_NON_CLASSE + log pour analyse.

---

## 6. DÉCISIONS À PRENDRE

| Décision | Options | Recommandation |
|----------|---------|----------------|
| Enrichir L3 ? | Oui / Non / Partiel | Oui — au moins 15–20 codes supplémentaires |
| Reprendre Phase A ? | Oui / Non | Oui — après correction du prompt et validation post-LLM |
| Conserver les 834 flagged ? | Oui / Purge / Re-run | Re-run après correction |

---

## 7. ANNEXES

### A. Codes L3 valides actuels (23)

```
4x4, abonnements_presse, antibiotiques, antipaludiques, camions, ciment, chaux, csp, DIVERS_NON_CLASSE, essence, gasoil, gilets, imprimantes, legumineuses, mais, masques_gants, mil_sorgho, ordinateurs, petrole, platre, plumpy_nut, riz, vitamines
```

### B. Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `scripts/classify_taxonomy_v2.py` | Phase A — à corriger |
| `scripts/seed_taxonomy_v2.py` | Taxonomie L1/L2/L3 — à enrichir |
| `docs/milestones/HANDOVER_M74_PHASE_A.md` | Handover — à mettre à jour |

---

*Rapport rédigé le 2026-03-07 · Agent Composer · À traiter par Tech Lead*
