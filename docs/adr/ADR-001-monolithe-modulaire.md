# ADR-001 — Architecture DMS : Monolithe Modulaire, Seuil Microservices & Trajectoire de Découpe

```
╔══════════════════════════════════════════════════════════════════════╗
║  ARCHITECTURE DECISION RECORD                                        ║
║  Référence  : ADR-DMS-001                                           ║
║  Statut     : PROPOSÉ — en attente validation CTO                   ║
║  Date       : 2026-04-08                                            ║
║  Auteur     : Architecture DMS / CTO Office                         ║
║  Audience   : CTO, Tech Lead, Produit, DevOps, Agents IA            ║
║  Hiérarchie : CONTEXT_ANCHOR.md > DMS_CANON_V5.1.0 > cet ADR       ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 1. Pourquoi cet ADR Existe

### 1.1 Le Problème Business

DMS traite des fonds publics et bailleurs pour SCI Mali. Il doit être **fiable avant d'être distribué**. La question "est-ce qu'on devrait passer en microservices" revient régulièrement. Sans cadre de décision formel, cette question provoque soit de l'inertie ("on ne touche à rien"), soit des découpes non contrôlées qui mettent la production en danger.

### 1.2 Le Problème Technique

Le codebase DMS est un monolithe de 129K lignes Python avec un service déjà extrait (`services/annotation-backend/`). La confusion entre **modularité du code** (packages, responsabilité unique, frontières explicites) et **architecture microservices** (runtimes séparés, contrats réseau, données distribuées) génère des décisions incohérentes.

### 1.3 Ce que cet ADR Tranche

Cet ADR répond à une seule question : **Quand et comment DMS passe-t-il d'un monolithe modulaire à des microservices ?** Il établit des critères objectifs, mesurables, et un processus de validation qui empêche à la fois l'immobilisme et la précipitation.

---

## 2. État des Lieux — Où En Est DMS Aujourd'hui

### 2.1 Architecture Actuelle

```
┌──────────────────────────────────────────────────────────────┐
│                    MONOLITHE MODULAIRE                        │
│                                                              │
│  main.py (FastAPI)                                           │
│  ├── src/api/routers/        → Routes HTTP                   │
│  ├── src/couche_a/           → Extraction, scoring, comité   │
│  ├── src/couche_b/           → Mercuriale, résolveurs        │
│  ├── src/cognitive/          → État cognitif E0→E6           │
│  ├── src/mql/                → MQL Engine V8 (V5.1)          │
│  ├── src/agent/              → Agent conversationnel (V5.1)  │
│  ├── src/services/           → PV, XLSX, signal engine       │
│  ├── src/auth/               → JWT, RBAC, guard              │
│  ├── src/db/                 → Pools, tenant context          │
│  └── src/workers/            → Jobs ARQ asynchrones          │
│                                                              │
│  PostgreSQL 16 (source de vérité unique)                     │
│  Redis 7 (cache, rate limit, contexte agent)                 │
│  106 migrations Alembic (chaîne linéaire)                    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  SERVICE EXTRAIT (déploiement séparé)                        │
│                                                              │
│  services/annotation-backend/                                │
│  ├── backend.py              → API Mistral, annotation       │
│  └── prompts/                → System prompts, validateur    │
│  Status: GELÉ (campagnes actives)                            │
│  Déploiement: Railway service indépendant                    │
│  Contrat: POST /predict (non versionné formellement)         │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Ce Qui a Déjà Été Fait (PR #344)

Le refactor PR #344 a porté sur la **modularisation interne** du monolithe :

- Décomposition de fichiers volumineux en packages
- `src/couche_a/extraction/` éclaté en sous-modules
- Pipeline A restructuré
- Durcissement CI
- Documentation de dette technique

**Ce n'était pas** une bascule microservices. C'était de l'hygiène de code. La distinction est fondamentale.

### 2.3 Contraintes Actives

| Contrainte | Source | Impact |
|---|---|---|
| Gel annotation-backend | `.cursor/rules/dms-annotation-backend-freeze.mdc` | Pas de modification structurelle sans mandat CTO post-campagne |
| Migrations Alembic | `docs/audit/ALEMBIC_STATE_2026-04-08.md` | Chaîne unique, head unique, pas de branches parallèles |
| Périmètre fermé | `CONTEXT_ANCHOR.md` RÈGLE-ANCHOR-08 | Toute modification hors périmètre nécessite mandat explicite |
| Base de données unique | Architecture actuelle | PostgreSQL est la source de vérité pour TOUS les modules |

---

## 3. Décisions

### D1 — Vocabulaire Opérationnel

Avant toute discussion technique, ces termes ont une signification précise et non négociable dans le contexte DMS :

| Terme | Définition DMS | Ce que ce N'EST PAS |
|---|---|---|
| **Monolithe modulaire** | Un dépôt, une app API principale, modules Python à frontières explicites, déploiement coordonné, une base de données. | Un fichier `main.py` de 10K lignes sans structure. |
| **Service extrait** | Un composant avec son propre runtime et déploiement, mais partageant la base de données et sans contrat réseau versionné formellement. | Un microservice au sens strict. |
| **Microservice** | Runtime déployable indépendamment, contrat réseau versionné (OpenAPI), propriété données isolée (schéma ou DB séparée), observabilité propre, rollback indépendant. | Un dossier `services/` ou un second conteneur Docker. |

**Conséquence immédiate** : L'annotation-backend est un **service extrait**, pas un microservice. DMS n'a **aucun** microservice au sens de D1.

### D2 — Position par Défaut

**Le monolithe modulaire est l'architecture dominante de DMS tant que les critères D4 ne sont pas remplis.**

Justification :

1. **Équipe** : 2-3 développeurs. Le coût opérationnel de microservices (réseau, auth distribuée, debugging, déploiements) dépasse la capacité de l'équipe.
2. **Données** : PostgreSQL avec RLS multi-tenant. Toutes les tables partagent `tenant_id`. Une séparation de données par service introduirait des transactions distribuées (sagas, outbox) sans bénéfice pour 50 utilisateurs.
3. **Cohérence** : Le scellement SHA-256 du PV (INV-W05) exige une transaction atomique sur snapshot + thread resolution + workspace status. C'est trivial dans un monolithe, complexe avec des services distribués.
4. **Vélocité** : Un changement de schéma = 1 migration Alembic + 1 déploiement. Pas 3 services à coordonner.

**Cela ne signifie PAS l'immobilisme.** La modularisation interne continue activement. Les frontières de modules sont renforcées. Les imports transversaux sont réduits. Mais tout reste dans un seul runtime déployable.

### D3 — Statut du Service Annotation-Backend

L'annotation-backend est un **cas spécial documenté** :

- Il est déployé séparément sur Railway (runtime indépendant)
- Son contrat API est `POST /predict` (non versionné formellement)
- Il est **gelé** pendant les campagnes d'annotation Label Studio
- Son évolution structurelle nécessite un **mandat CTO explicite post-gel**

**Ce qu'il prouve** : DMS sait extraire un service quand c'est justifié (charge LLM, cycle de vie indépendant des campagnes). Ce qu'il ne prouve pas : que tout DMS devrait être découpé de la même façon.

### D4 — Seuil de Bascule Microservice

Une nouvelle découpe en microservice (runtime + déploiement séparé) n'est envisageable que si les **5 critères cumulatifs** suivants sont validés par le CTO :

```
CRITÈRE 1 — BESOIN DÉMONTRÉ
───────────────────────────────────────────────────────────────
La charge, la taille de l'équipe, le blast radius ou le cycle
de release justifient la complexité opérationnelle additionnelle.

Mesure : au moins UN des indicateurs suivants est dépassé :
  • > 200 utilisateurs simultanés sur le composant ciblé
  • > 2 équipes travaillent sur le même module en parallèle
  • Un incident prod du composant a impacté un domaine non relié
  • Le cycle de release du composant est > 3× plus fréquent que le reste

CRITÈRE 2 — CONTRAT STABLE
───────────────────────────────────────────────────────────────
L'API ou les événements entre le nouveau service et le monolithe
sont versionnés, documentés (OpenAPI), et testés.

Mesure :
  • Spec OpenAPI du contrat existe et est gelée
  • Tests consumer/provider existent dans CI
  • Le contrat n'a pas changé plus de 2× dans les 3 derniers mois

CRITÈRE 3 — PROPRIÉTÉ DONNÉES CLAIRE
───────────────────────────────────────────────────────────────
Les règles de consistance sont écrites et acceptées.

Mesure :
  • Document décrivant : quelles tables appartiennent au service
  • Si transactions cross-service : pattern saga/outbox/idempotence documenté
  • Si données partagées : vue matérialisée ou API de synchronisation documentée

CRITÈRE 4 — OBSERVABILITÉ OPÉRATIONNELLE
───────────────────────────────────────────────────────────────
Le nouveau service a sa propre observabilité et peut être rollback
indépendamment.

Mesure :
  • Logs structurés par service (pas mélangés dans stdout monolithe)
  • Métriques par service (latence, erreurs, saturation)
  • Traces distribuées si appels cross-service (Langfuse ou OpenTelemetry)
  • Runbook de rollback indépendant documenté

CRITÈRE 5 — MANDAT CTO
───────────────────────────────────────────────────────────────
Le CTO a émis un mandat écrit nommant :
  • Les fichiers/modules concernés
  • Les risques identifiés et les mitigations
  • La fenêtre de déploiement
  • Le respect des gels en cours (annotation, Alembic)
  • Le plan de rollback si la découpe échoue
```

**Si D4 n'est pas intégralement rempli**, toute demande "passer en microservices" est traitée comme une **évolution modulaire dans le monolithe** ou un **ADR complémentaire** ciblant un boundary précis.

### D5 — Trajectoire de Découpe (Pattern Strangler)

Si D4 est validé pour un boundary spécifique, la découpe suit ce processus en 4 étapes. Pas de big bang.

```
ÉTAPE 1 — ISOLER
─────────────────────────────────────────────────────
Créer un module Python avec une interface explicite.
Aucun import direct depuis l'extérieur du module.
Tous les appels passent par des fonctions publiques documentées.
Le module vit DANS le monolithe. Pas de réseau.
Durée : 1-2 semaines.

ÉTAPE 2 — CONTRACTUALISER
─────────────────────────────────────────────────────
Définir le contrat OpenAPI du futur service.
Implémenter les tests consumer/provider.
Le module expose DÉJÀ son contrat via une route interne
dans le monolithe (/internal/module-name/...).
Les appelants migrent vers cette route interne.
Durée : 1-2 semaines.

ÉTAPE 3 — EXTRAIRE
─────────────────────────────────────────────────────
Déployer le module comme service séparé (Railway service).
Configurer les routes de proxy dans le monolithe.
Les 2 chemins coexistent : interne (monolithe) + réseau (service).
Feature flag pour basculer.
Durée : 1 semaine.

ÉTAPE 4 — COUPER
─────────────────────────────────────────────────────
Quand le service externe est stable (2 semaines de prod) :
Supprimer le chemin interne.
Le module est un microservice indépendant.
Durée : 1 semaine.

TOTAL : 4-6 semaines par boundary.
```

**Règle absolue** : on n'extrait qu'**un seul** boundary à la fois. Mesurer. Stabiliser. Puis décider du suivant.

---

## 4. Candidats Potentiels de Découpe Future

Cette section identifie les boundaries qui **pourraient** être extraits si D4 est rempli. Ce n'est **pas** un plan d'extraction. C'est une carte de possibilités.

| Boundary | Justification potentielle | D4 rempli aujourd'hui ? | Horizon |
|---|---|---|---|
| **Agent + MQL** | Charge LLM indépendante de l'API CRUD, cycle de release potentiellement plus rapide | Non (< 200 users, même équipe) | V5.3+ si adoption multi-pays |
| **Génération documentaire** | Jobs lourds (WeasyPrint, openpyxl), blast radius isolable | Non (ARQ worker suffit) | V6+ si volume PV > 100/jour |
| **Extraction pipeline** | Charge OCR/LLM intensive, déjà partiellement isolé | Partiel (annotation-backend existe) | Post-gel annotation |
| **Market data ingestion** | Cycle de vie différent (batch vs CRUD), données potentiellement séparables | Non (même schéma, mêmes tenants) | V5.3+ si sources > 50 campagnes |

**Aucun de ces candidats ne justifie une extraction aujourd'hui.** Le monolithe avec workers ARQ absorbe la charge actuelle sans problème.

---

## 5. Alternatives Considérées

### Alternative A — Microservices Immédiat

Découper DMS en 5-6 services dès maintenant (API, Agent, Extraction, DocGen, Market, Auth).

| Avantage | Inconvénient |
|---|---|
| Scaling indépendant par service | Coût ops × 6 (déploiements, monitoring, debugging) |
| Ownership claire par domaine | 2-3 développeurs ne peuvent pas maintenir 6 services |
| Cycle de release découplé | Transactions distribuées pour le scellement (INV-W05) |

**Rejeté.** Le coût opérationnel dépasse largement la capacité de l'équipe et le bénéfice pour 50 utilisateurs.

### Alternative B — Statu Quo Sans Modularisation

Garder le monolithe tel quel, sans investir dans la modularisation interne.

| Avantage | Inconvénient |
|---|---|
| Zéro friction refactor | Fichiers > 800 lignes, imports croisés, tests fragiles |
| Pas de risque de régression refactor | Vélocité qui baisse avec le temps |

**Rejeté.** La dette technique accumulée ralentit le développement. La modularisation interne est nécessaire.

### Alternative C — Monolithe Modulaire + Extractions Ponctuelles (RETENUE)

Investir dans la modularité interne. Extraire un service uniquement quand D4 est rempli. Pattern strangler, un boundary à la fois.

| Avantage | Inconvénient |
|---|---|
| Aligné avec la taille de l'équipe | Ne satisfait pas les attentes "architecture distribuée" |
| Un seul déploiement, une seule DB, transactions simples | Risque de "grosse boule de boue" si modularisation insuffisante |
| Extractions futures possibles sans big bang | Chaque extraction prend 4-6 semaines |

**Retenue.** C'est le compromis optimal entre vélocité, fiabilité et évolutivité.

---

## 6. Conséquences

### 6.1 Ce Qui Change Immédiatement

| Pour qui | Ce qui change |
|---|---|
| **Développeurs** | "Refactorer un fichier" n'est pas "créer un microservice". Les deux sont nécessaires mais distincts. Toute PR de modularisation reste dans le monolithe sauf mandat D4. |
| **Agents IA (Cursor/Opus)** | Quand un mandat dit "modulariser", cela signifie package Python, pas runtime séparé. Quand un mandat dit "extraire en service", les 5 critères D4 doivent être référencés. |
| **Produit** | L'architecture est un monolithe performant. La roadmap produit ne doit pas être bloquée par des considérations d'architecture distribuée qui ne sont pas justifiées. |
| **DevOps** | Railway reste le modèle de déploiement. Un monolithe + workers + annotation-backend. Pas de mesh de 6 services. |

### 6.2 Ce Qui Ne Change Pas

- Les gels existants restent en vigueur (annotation-backend, Alembic)
- La chaîne de migrations Alembic reste unique et linéaire
- Le Canon V5.1.0 reste la source de vérité architecture
- PostgreSQL reste la source de vérité données unique

### 6.3 Risques si cet ADR N'est Pas Respecté

| Risque | Impact | Probabilité |
|---|---|---|
| Découpage non contrôlé par un développeur ou agent IA | Incidents prod, double source de vérité, migrations conflictuelles | Moyenne — les agents IA peuvent interpréter "modulariser" comme "extraire" |
| Blocage permanent "on ne touche à rien" | Vélocité qui s'effondre, dette technique irréversible | Faible — la pression produit pousse à l'action |
| Extraction prématurée d'un service sans observabilité | Debugging impossible en prod, MTTR qui explose | Moyenne — tentation de "faire propre" sans infrastructure ops |

---

## 7. Gouvernance et Cycle de Vie

### 7.1 Validation

```
POUR ACCEPTER cet ADR :
  □ Le CTO signe (commentaire sur le PR ou commit avec "ADR-001: ACCEPTÉ")
  □ Une ligne d'addendum est ajoutée dans CONTEXT_ANCHOR.md :
    "2026-04-08 | ADR-001 monolithe modulaire | ACCEPTÉ | SHA: ..."
  □ Le statut en tête de ce document passe de PROPOSÉ à ACCEPTÉ

POUR REJETER cet ADR :
  □ Le CTO documente le motif de rejet
  □ Un ADR alternatif est proposé dans les 2 semaines
```

### 7.2 Révision

Cet ADR est révisé si :

- Un premier microservice "seuil D4" est validé → nouvel ADR fils
- L'équipe dépasse 5 développeurs → réévaluer D4 critère 1
- Le nombre d'utilisateurs dépasse 500 → réévaluer D4 critère 1
- Un incident prod prouve qu'un boundary aurait dû être isolé → réévaluer D4 critère 1

### 7.3 Traçabilité

| Date | Événement | Référence |
|---|---|---|
| 2026-04-08 | ADR-001 proposé | Ce document |
| — | Validation CTO | En attente |
| — | Premier seuil D4 atteint | ADR futur |

---

## 8. Références

| Document | Rôle |
|---|---|
| `docs/freeze/CONTEXT_ANCHOR.md` | Hiérarchie des autorités, gels, RÈGLE-ANCHOR-08 |
| `docs/freeze/DMS_CANON_V5.1.0_FREEZE.md` | Architecture technique de référence |
| `.cursor/rules/dms-annotation-backend-freeze.mdc` | Gel service annotation |
| `.cursor/rules/file-decomposition.mdc` | Seuils lignes, découpe modules |
| `docs/audit/DMS_TECHNICAL_DEBT_P0_P3.md` | Contexte dette technique |
| `docs/audit/ALEMBIC_STATE_2026-04-08.md` | État migrations |
| PR #344 | Refactor modulaire monolithe (pas microservices) |

---

```
Statut    : PROPOSÉ
Prochain  : Validation CTO → ACCEPTÉ ou REJETÉ
Fichier   : docs/adr/ADR-001-monolithe-modulaire.md
```
