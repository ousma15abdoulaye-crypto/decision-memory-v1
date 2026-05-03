# ADR-P34-INFRA-PHASE2-IDEBT1-BACKEND-DIAGNOSTIC-V1

**Référence** : ADR-P34-INFRA-PHASE2-IDEBT1-BACKEND-DIAGNOSTIC-V1
**Date proposition** : 2026-04-22
**Date signature** : 2026-04-22
**Rédaction** : CTO Senior DMS (successeur)
**Signature** : CTO principal DMS — APPROUVÉ
**Chantier parent** : P3.4-INFRA-STABILIZATION
**Phase cible** : Phase 2 I-DEBT-1 — Backend annotation extraction
**Fragments prévus** : P2-A, P2-B, P2-C, P2-D, P2-E

---

## 1. Contexte

Le chantier P3.4-INFRA-STABILIZATION a franchi deux jalons majeurs :

- **Phase 1 I-DEBT-2 DB stable** : close sur diagnostic opposable
  (cf. `decisions/phase1/L1_E_phase1_synthesis.md`). SLO-1 🔴 ROUGE
  (`/health` p95 1.09s) et SLO-3 🔴 FAIL (tunnel rupture 15 min) mesurés.

- **Sous-chantier P3.4-INFRA-WORKER-DEPLOYMENT** : clos sur Option C
  validée architecturalement (cf. `decisions/worker/W5_worker_synthesis_phase2_readiness.md`).
  Worker Railway interne `dms-db-worker` opérationnel, blocage infra levé.

La **Phase 2 I-DEBT-1** peut donc s'ouvrir sur la dette infra identifiée
dans le contrat P3.4-INFRA-STABILIZATION :

> **I-DEBT-1** : Backend annotation extraction timeout 120s sous charge OCR

**SLO cible de clôture Phase 2** :
- SLO-2 : extraction 1 doc réel p95 < 30s

**Contexte complémentaire opposable** :
- Finding L1-A : backend `/health` déjà à p95 1.09s au repos
  (2.2× SLO cible 500ms) → marge étroite avec SLO-2 sous charge
- Hypothèse non vérifiée L1-A : `/health` fait des checks internes
  (DB, Mistral, etc.) pas juste `return ok`
- Cause racine potentielle I-DEBT-1 : backend Railway sous-dimensionné
  qui cascade sur extraction OCR
- Plan Directeur Pipeline Core V1.1 §01B : 200+ documents réels intégrés,
  110 avec ground truth, corpus multi-zones Mali

## 2. Décision

Ouvrir la **Phase 2 I-DEBT-1 — Backend annotation extraction diagnostic**
sous discipline infra-stabilization stricte, avec :

1. **Périmètre diagnostic uniquement** (pas de correctif code métier)
2. **Fragmentation en 5 fragments** P2-A → P2-E (discipline G32)
3. **Sélection documentaire actée CTO principal** :
   - P2-A : dossier **GCF** (ITT + fournisseurs AZ et ATMOST)
   - P2-B : dossier **PADEM** (TDR + fournisseur BECATE)
   - P2-C : dossier **Cartouche** (processus complet)
   - P2-D et P2-E : agnostiques au dossier
4. **Instrumentation autorisée** (logs, métriques, profiling non-intrusif)
   **distinguée de la modification logique métier** (interdite, STOP-INFRA-1)
5. **Usage worker `dms-db-worker` passif** (requêtes DB si nécessaires,
   pas d'extension endpoints worker dans Phase 2)

## 3. Périmètre strict

### IN — actions autorisées Phase 2

- **Mesure** : latence, throughput, CPU, RAM, durée extraction, taux d'erreur
- **Instrumentation** :
  * Logs structurés additionnels dans `services/annotation-backend/`
    avec guards env var (`DMS_PHASE2_INSTRUMENTATION=1`)
  * Métriques Railway dashboard (lecture seule)
  * Profiling Python (`cProfile`, `py-spy`) lancé en dev, pas en prod
  * Requêtes DB diagnostiques read-only via worker `dms-db-worker` ou psql
- **Corpus** : lecture documents réels du workspace pilote `CASE-28b05d85`
  (UUID `f1a6edfb-ac50-4301-a1a9-7a80053c632a`) selon sélection CTO
- **Documentation** : 5 livrables `decisions/phase2/P2_*.md`

### OUT — actions interdites Phase 2

- **Modification logique métier** : aucun changement algorithme, pipeline,
  scoring, matrice, éligibilité (STOP-INFRA-1 maintenu)
- **Modification critique code** : pas de refactor, pas d'optimisation,
  pas de "fix tant qu'on y est"
- **Modification config Railway en prod** : pas de changement CPU/RAM/replicas
  sans mandat dédié et arbitrage CTO principal
- **Correctif I-DEBT-1** : Phase 2 est diagnostic pur, le correctif
  relèvera d'un mandat séparé post-Phase 2
- **Relance E4-quater** : STOP-INFRA-3 maintenu
- **Merge PR #430 Draft** : inchangé
- **Modification worker `dms-db-worker`** : pas d'extension endpoints
  (sauf mandat dédié si blocage diagnostic P2-C)
- **Ouverture Phase 3** : non autorisée avant P2-E validé
- **Chantiers latents CL-1 à CL-6** : reportés

### Frontière opposable instrumentation vs modification logique métier

| Action | Catégorie | Statut |
|---|---|---|
| Ajouter `logger.info(...)` en début/fin de fonction | Instrumentation | ✅ IN |
| Wrapper fonction avec décorateur `@timer` | Instrumentation | ✅ IN |
| Ajouter `time.perf_counter()` autour d'un appel externe | Instrumentation | ✅ IN |
| Modifier algo d'extraction, changer ordre étapes | Logique métier | 🔴 OUT |
| Changer timeout hardcodé (120s → autre) | Logique métier | 🔴 OUT |
| Ajouter retry, circuit breaker, fallback | Logique métier | 🔴 OUT |
| Guard env var `DMS_PHASE2_INSTRUMENTATION` | Instrumentation | ✅ IN |
| Modifier valeur par défaut config métier | Logique métier | 🔴 OUT |

**Règle doctrinale** : si une ligne de code modifie **ce que fait le
système** en production normale (sans flag instrumentation), c'est OUT.
Si elle modifie **ce que le système expose** sur son fonctionnement
(avec flag optionnel), c'est IN.

## 4. Fragmentation Phase 2

### P2-A — Baseline extraction dossier GCF

**Dossier** : GCF — ITT + fournisseurs AZ et ATMOST (périmètre réduit,
maîtrisable, baseline)

**Objectif** : mesurer latence extraction nominale sur dossier réduit
contrôlé. Obtenir une baseline avant montée en charge.

**Livrable** : `decisions/phase2/P2_A_baseline_extraction_gcf.md`

**SLO intermédiaire indicatif** : extraction dossier GCF complet
< 60s (baseline, pas cible SLO-2)

**Budget agent** : 60-75 min

### P2-B — Charge intermédiaire dossier PADEM

**Dossier** : PADEM — TDR + fournisseur BECATE (périmètre intermédiaire)

**Objectif** : caractériser charge backend (CPU/RAM/latence) pendant
extraction réelle sur dossier intermédiaire. Identifier si SLO-2
(30s par doc) est atteint.

**Livrable** : `decisions/phase2/P2_B_charge_extraction_padem.md`

**SLO mesuré** : SLO-2 cible p95 < 30s par document

**Budget agent** : 75-90 min

### P2-C — Stress systémique dossier Cartouche

**Dossier** : Cartouche — processus complet (périmètre systémique)

**Objectif** : reproduire le timeout 120s observé en production, caractériser
les conditions exactes de dégradation sous charge réelle pipeline complet.

**Livrable** : `decisions/phase2/P2_C_stress_extraction_cartouche.md`

**SLO confirmé** : SLO-2 sous charge systémique

**Budget agent** : 90-120 min

### P2-D — Diagnostic cause racine I-DEBT-1

**Objectif** : analyser les données P2-A/B/C, identifier la ou les causes
racines du timeout 120s (backend sous-dimensionné ? Mistral lent ?
DB bottleneck ? pipeline séquentiel ? autre ?), **sans correctif**.

**Livrable** : `decisions/phase2/P2_D_root_cause_analysis.md`

**Budget agent** : 60 min (analyse, pas mesure)

### P2-E — Synthèse Phase 2 et décision Phase 3

**Objectif** : synthèse opposable Phase 2, verdicts SLO-2, matrice
d'options de correctif (pour arbitrage CTO principal futur), transition
vers Phase 3 I-DEBT-3 runbook ops.

**Livrable** : `decisions/phase2/P2_E_phase2_synthesis.md`

**Budget agent** : 30 min

## 5. Options considérées et écartées

| Option | Description | Raison du rejet |
|---|---|---|
| Phase 2 comme sous-chantier dédié `P3.4-INFRA-BACKEND-DIAGNOSTIC` | Nom distinct du chantier parent | Phase 2 est une phase du chantier parent, pas un sous-chantier ; cohérent avec handover V4 §3.3 ; structure plus simple |
| Fragmentation 3 fragments uniquement | Économie | Discipline G32 éprouvée sur L1-A→L1-E (5 fragments) ; 3 fragments trop denses |
| Extension worker avec endpoints `/benchmark/extract` | Instrumentation avancée | Prématuré ; `(γ)` worker passif suffit pour P2-A/B/C, extension envisageable si blocage |
| Correctif I-DEBT-1 dans Phase 2 | Gain de temps | Viole STOP-INFRA-1 frontière ; le diagnostic pur est plus robuste doctrinalement |
| Sélection dossier unique (1 document) | Simplicité | Ne permet pas la progression diagnostique maîtrisé → systémique ; sélection CTO GCF/PADEM/Cartouche est supérieure |

## 6. Conséquences

### Positives

- Diagnostic SLO-2 opposable sur 3 dossiers réels représentatifs
- Progression maîtrisé → systémique permet d'isoler les causes
- Worker `dms-db-worker` amorti (pattern interne Railway validé)
- Frontière instrumentation/logique métier tracée opposablement
- Pattern 5 fragments reproduit (discipline établie Phase 1)

### Négatives et mitigations

- **Risque d'instrumentation intrusive** malgré guard env var
  → mitigation : revue CTO Senior ligne à ligne de tout commit
  contenant modification `services/annotation-backend/`
- **Budget temps total Phase 2 estimé ~5-6h agent**
  → mitigation : fragmentation + checkpoints par fragment
- **Risque découverte cause racine nécessitant modification infra
  Railway (scale-up)** → mitigation : Phase 2 produit matrice
  d'options, correctif sous mandat séparé post-Phase 2
- **Risque dossier sélectionné indisponible dans workspace pilote**
  → mitigation : STOP agent + remontée CTO principal, pas de substitution

### Neutres

- PR #430 Draft reste non mergée
- STOP-INFRA-1 et STOP-INFRA-3 maintenus
- Chantiers latents CL-1 à CL-6 toujours reportés

## 7. Gouvernance

### Séquence d'émission mandats

```
ADR signé (ce document)
    ↓
Mandat P2-A émis → exécution agent → rapport → validation CTO Senior
    ↓
Mandat P2-B émis → exécution agent → rapport → validation CTO Senior
    ↓
Mandat P2-C émis → exécution agent → rapport → validation CTO Senior
    ↓
Mandat P2-D émis → analyse agent → rapport → validation CTO Senior
    ↓
Mandat P2-E émis → synthèse agent → rapport → validation CTO Senior
    ↓
Clôture Phase 2 actée par CTO principal
    ↓
Ouverture Phase 3 I-DEBT-3 sous mandat dédié
```

### Signaux STOP durs spécifiques Phase 2

- **STOP-P2-1** : modification logique métier sans guard env var → commit refusé
- **STOP-P2-2** : dossier sélectionné (GCF/PADEM/Cartouche) indisponible
  → remontée, pas de substitution unilatérale
- **STOP-P2-3** : timeout ou erreur systémique backend > 3 tentatives
  sur un fragment → remontée arbitrage CTO principal
- **STOP-P2-4** : découverte défaut critique sécurité (secret exposé,
  injection, etc.) → STOP immédiat

### Supervision

- CTO Senior successeur : émission mandats, checkpoints, validation recevabilité
- CTO principal : arbitrage sur STOP durs, validation clôture phase
- Agent Claude Code : exécution stricte dans cadre mandats

## 8. Statut

- ✅ Signé par CTO principal DMS — 2026-04-22 — APPROUVÉ
- Décision opposable en vigueur
- Déclenche émission mandat P2-A

---

**Signé** : CTO principal DMS (APPROUVÉ 2026-04-22)
