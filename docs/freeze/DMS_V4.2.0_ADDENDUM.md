# DMS V4.2.0 — ADDENDUM WORKSPACE-FIRST

**Référence** : DMS-V4.2.0-ADDENDUM-WORKSPACE
**Date de freeze** : 2026-04-04
**Statut** : FREEZE DÉFINITIF après hash
**Auteur** : Abdoulaye Ousmane — Founder & CTO
**Complémente** : DMS V4.1.0 FREEZE (2026-02-26)
**Supersède** : DMS-PLAN-FINAL-2026-04-02 Partie V (amendée)
**Review** : 4 BLOC corrigés, 2 OBS intégrées, séquence complète semaines 0→10

---

## CLAUSE DE HIÉRARCHIE DOCUMENTAIRE

> Ce document est un **ADDENDUM** au canon V4.1.0 FREEZE.
> Il ne remplace pas le canon. Il le complète sur les espaces que le canon laisse ouverts.
>
> **Ce qu'il modifie explicitement :**
> - La table `cases` est dépréciée au profit de `process_workspaces`
> - 5 tables comité/registre du canon sont dépréciées (voir §3.4)
> - Le RBAC 5 rôles est étendu à 17 permissions × 6 rôles
> - 8 invariants workspace (INV-W01→W08) et 1 règle (RÈGLE-W01) sont ajoutés
> - Les milestones M16A→M21 sont satisfaits par les migrations workspace
> - Le Plan Final 2026-04-02 Partie V "Interdit jusqu'à M15" est amendé
>
> **Ce qu'il ne modifie PAS :**
> - RÈGLE-01 à RÈGLE-29
> - RÈGLE-ORG-01 à RÈGLE-ORG-11
> - INV-R1 à INV-R9 (adaptés au workspace, jamais supprimés)
> - Les SLA (UPLOAD ≤500ms, EXTRACT ≤30s, PIPELINE ≤60s, SIGNAL ≤200ms, EXPORT ≤10s)
> - La stack infrastructure (FastAPI, PostgreSQL 16, Redis 7, ARQ, Railway, Alembic)
> - Les migrations existantes 001→067
>
> **En cas de conflit :**
> - Sur les RÈGLES, RÈGLE-ORG, INV-R, SLA → **le canon V4.1.0 prime**
> - Sur l'unité métier, le schéma workspace, INV-W, le RBAC → **ce document prime**

---

## PARTIE I — DIAGNOSTIC ET DÉCISION DE DÉPRÉCIATION

### 1.1 Les 3 failles structurelles prouvées

**Faille 1 — Le trou M12→M14** (P1-M14-01)

```python
# src/procurement/m14_engine.py — l'état réel
for offer in inp.offers:  # ← QUI PRODUIT CETTE LISTE ?
    scores = evaluate_offer(offer, criteria)
```

*Preuve audit* : DMS-MAP-M0-M15-001 §4 — M14 `runtime_status: substantial_but_open`, note : "offers[] fourni en entrée — pas d'assembleur canonique process-only dans ce module."

*Preuve code* : `m14_engine.py` consomme `inp.offers` comme entrée. M12 classifie des documents individuels. Personne ne transforme les documents classifiés en offres groupées par fournisseur.

*Impact* : Le pipeline M12→M14 ne peut pas fonctionner de bout en bout sans intervention manuelle pour construire la liste `offers[]`. Le système est structurellement incomplet.

**Faille 2 — Le comité est externe au système**

*Preuve audit* : DMS-MAP-M0-M15-001 §13 — "Workspace-first : non — le produit exposé reste très pipeline/API/document."

*Preuve schéma* : `evaluation_documents` a `aco_excel_path` et `pv_word_path`. Le comité reçoit un export, délibère dans Word/Excel, retourne un scan signé. DMS est un générateur de fichiers, pas un environnement de décision.

*Impact* : Chaque délibération hors DMS est une rupture de traçabilité. L'auditeur ne peut pas prouver que le PV reflète la délibération réelle.

**Faille 3 — La mémoire marché est enfermée dans `case_id`**

*Preuve audit* : DMS-MAP-M0-M15-001 §8 — "Couche B hors processus : Données OK ; surface produit limitée par API/UI et auth."

*Preuve code* : `market_surveys.case_id` est optionnel mais toutes les routes d'accès passent par un contexte de case. Un procurement officer ne peut pas interroger le prix du ciment à Mopti sans ouvrir un dossier.

*Impact* : L'actif différentiel de DMS (la mémoire marché cumulative) est inaccessible à l'utilisateur qui en a le plus besoin — celui qui prépare un processus et veut des données avant de lancer.

### 1.2 Pourquoi la dépréciation totale — pas le wrapper

| Option | Description | Verdict |
|---|---|---|
| **A. Dépréciation totale** | `cases` disparaît. `process_workspaces` est l'unique racine. 12 tables migrées. | **Seule option viable** |
| B. Wrapper (FK nullable) | `process_workspaces` wrappe `cases`. workspace_id ajouté en parallèle. | "Progressive = jamais terminée" |
| C. Coexistence | Deux objets racine sans lien. | Deux sources de vérité = violation RÈGLE-04 |

**Arguments contre le wrapper :**
- Crée une double hiérarchie `workspace_id` + `case_id` sur chaque artefact — confusion permanente pour l'agent et le développeur
- "Migration progressive" signifie qu'à M21, certains artefacts pointent vers `cases`, d'autres vers `workspaces`, certains vers les deux — schizophrénie architecturale
- Les 1737 tests qui testent `case_id` testent le mauvais modèle — les préserver c'est préserver l'erreur structurelle
- 12 ALTER TABLE est du travail, pas un risque — c'est faisable en 1 semaine concentrée

**Le coût réel :**

```
Tables avec FK vers cases(id) à migrer : 12
  documents, evaluation_criteria, offer_extractions,
  extraction_review_queue, score_history, elimination_log,
  evaluation_documents, decision_history, dict_proposals,
  market_surveys, committees (→ remplacé), submission_registries (→ remplacé)

Tables dépréciées (remplacées par nouvelles) : 6
  cases, committees, committee_members, committee_delegations,
  submission_registries, submission_registry_events

Estimation tests à adapter : 200-300 sur 1737 (grep case_id tests/)
Estimation durée migration données : 1 jour
Estimation durée adaptation tests : 2-3 jours
```

---

## PARTIE II — L'EXPÉRIENCE UTILISATEUR CIBLE

### 2.1 Avant DMS (la réalité terrain SCI Mali)

```
LUNDI 8h    Reçoit un email avec 15 fichiers ZIP d'un DAO
            Crée un dossier sur son bureau Windows
            Imprime les TDR pour lire tranquillement

LUNDI 14h   Ouvre Excel, crée un tableau comparatif vide
            Copie-colle les prix de chaque offre manuellement
            Se trompe sur une ligne → recommence

MARDI       Cherche la mercuriale 2025 Mopti dans ses emails
            Ne la trouve pas → appelle un collègue à Bamako
            Compare les prix à la main → 2h de travail

MERCREDI    Rédige le PV dans Word
            Copie les scores depuis Excel → erreur de formule
            Le comité se réunit → discute sur papier
            Le président signe → scan → email → archivé nulle part

RÉSULTAT    5 jours. 3 erreurs. 0 traçabilité. 0 mémoire.
```

### 2.2 Avec DMS workspace-first

```
LUNDI 8h    Drag & drop le ZIP dans DMS
            Le temps du café, DMS a :
            → Extrait tous les documents (Mistral OCR 3, < 30s)
            → Assemblé 4 bundles fournisseurs avec complétude visible
            → Classifié chaque document (M12)
            → Signalé 1 bundle incomplet (manque RIB) → notification
            → Détecté le framework SCI, appliqué le profil DGMP Mali

LUNDI 9h    Ouvre son workspace. Voit :
            4 fournisseurs | 1 incomplet | 12 docs
            SARL KONATÉ     85%  complet
            ETS DIALLO      82%  complet
            GROUPE TOURÉ    67%  attention
            CABINET SIDIBÉ   0%  RIB manquant

LUNDI 10h   Clique sur Marché → W2 s'ouvre
            Voit : ciment SARL KONATÉ = +40% vs mercuriale Mopti T1 2026
            DMS NE DIT PAS "ce fournisseur est trop cher"
            DMS DIT : "écart mercuriale : +40%. 3 observations.
            Signal quality : medium"
            L'officer comprend immédiatement.

LUNDI 14h   L'évaluation M14 est prête. Ouvre Évaluation
            Matrice de scores par critère, par fournisseur
            Flags éliminatoires visuels (NIF absent → rouge)
            Écarts mercuriale intégrés
            AUCUN ranking. AUCUNE recommandation. Les faits.

MARDI       Le comité se connecte à DMS (W3)
            Même vue que l'officer — pas d'export Excel
            Le président ouvre la session de délibération
            Chaque membre commente, conteste un score,
            demande une clarification → tout tracé temps réel
            Le président scelle → PV auto SHA-256 + snapshot

RÉSULTAT    2 jours. 0 erreur copie. Traçabilité totale.
            La mercuriale mise à jour avec le prix payé.
            Le prochain processus en bénéficie.
```

### 2.3 Les 7 moments addictifs

| # | Moment | Ce qui se passe | Effet utilisateur |
|---|---|---|---|
| 1 | **Drop du ZIP** | 15 fichiers → 4 bundles en 30s | "J'ai gagné 4 heures de tri" |
| 2 | **Bundle incomplet** | Notification : "SIDIBÉ — RIB manquant" | "Le système a vu ce que j'aurais oublié" |
| 3 | **Écart mercuriale** | "+40% vs Mopti T1 2026" | "Je sais négocier maintenant" |
| 4 | **Matrice M14** | Scores × critères, flags, sans ranking | "C'est le tableau que je faisais en 2h" |
| 5 | **Délibération live** | Comité voit la même chose, en même temps | "Plus de 'tu as quelle version ?'" |
| 6 | **Scellement PV** | SHA-256, snapshot, irréversible | "L'auditeur ne peut plus rien me reprocher" |
| 7 | **Mémoire cumulative** | "Ciment Mopti +12% en 6 mois" (W2) | "Je vois la tendance avant de lancer" |

### 2.4 Structure workspace — 4 zones

```
W0 — SHELL
  "Mes processus" | "Marché" | "Historique" | "Mon compte"

  W1 — PROCESS WORKSPACE (dans un processus)
    BUNDLES    | ÉVALUATION | COMITÉ   | MARCHÉ CONTEXT
    4 frs      | matrice    | session  | mercuriale
    docs       | scores     | délibér. | écarts
    complétude | flags      | votes    | signaux
    HITL       | AUCUN      | scellé   |
               | RANKING    | PV auto  |

  W2 — MARKET INTELLIGENCE (hors processus)
    Mercuriales | Indices | Fournisseurs | Watchlists
    Interrogeable SANS workspace_id

  W4 — MEMORY (patterns cumulatifs — post-pilote)
    Processus similaires | Tendances prix | Fiabilité
```

---

## PARTIE III — SCHÉMA DB CIBLE

Référence DDL complète : `docs/freeze/DMS_V4.2.0_SCHEMA.sql`

### 3.1 Nouvelles tables

| Table | Migration | Nature | RLS |
|---|---|---|---|
| `tenants` | 068 | CRUD | Non (référence globale) |
| `process_workspaces` | 069 | CRUD + FSM sealed irréversible | Oui |
| `workspace_events` | 069 | APPEND-ONLY | Oui |
| `workspace_memberships` | 069 | CRUD — UNIQUE(workspace_id, user_id, role) BLOC-03 | Non |
| `supplier_bundles` | 070 | CRUD | Oui |
| `bundle_documents` | 070 | CRUD | Oui |
| `committee_sessions` | 071 | CRUD + FSM sealed irréversible | Oui |
| `committee_session_members` | 071 | CRUD | Non |
| `committee_deliberation_events` | 071 | APPEND-ONLY | Oui |
| `vendor_market_signals` | 072 | APPEND-ONLY | Non |
| `market_watchlist_items` | 072 | CRUD | Non |
| `rbac_permissions` | 075 | Référence | Non |
| `rbac_roles` | 075 | Référence | Non |
| `rbac_role_permissions` | 075 | Référence | Non |
| `user_tenant_roles` | 075 | CRUD | Non |

### 3.2 Tables dépréciées

| Table canon V4.1.0 | Remplacée par | Migration |
|---|---|---|
| `cases` | `process_workspaces` | 073→074 |
| `committees` | `committee_sessions` | 071 |
| `committee_members` | `committee_session_members` | 071 |
| `committee_delegations` | champ `delegate_*` dans `committee_session_members` | 071 |
| `submission_registries` | `workspace_events` type `submission_*` | 069 |
| `submission_registry_events` | `workspace_events` + `committee_deliberation_events` | 069+071 |

### 3.3 Tables canon modifiées — Migration 073

```sql
-- Ajout workspace_id sur 10 tables (nullable temporairement)
ALTER TABLE documents ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE evaluation_criteria ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE offer_extractions ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE extraction_review_queue ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE score_history ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE elimination_log ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE evaluation_documents ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE decision_history ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE dict_proposals ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);
ALTER TABLE market_surveys ADD COLUMN workspace_id UUID REFERENCES process_workspaces(id);

-- Contrainte CHECK INV-W06 sur evaluation_documents
ALTER TABLE evaluation_documents ADD CONSTRAINT no_winner_field CHECK (
    (scores_matrix IS NULL) OR (
        (scores_matrix->>'winner') IS NULL AND
        (scores_matrix->>'rank') IS NULL AND
        (scores_matrix->>'recommendation') IS NULL AND
        (scores_matrix->>'best_offer') IS NULL AND
        (scores_matrix->>'selected_vendor') IS NULL
    )
);
```

### 3.4 Corrections BLOC-01 à BLOC-04

**BLOC-01** — Script migration : whitelist `frozenset` + assertion avant interpolation.
Voir `DMS_V4.2.0_MIGRATION_PLAN.md` §script.

**BLOC-02** — `map_status` : exception explicite, pas de default silencieux.
Voir `DMS_V4.2.0_MIGRATION_PLAN.md` §script.

**BLOC-03** — `workspace_memberships` : UNIQUE sur `(workspace_id, user_id, role)` pas `(workspace_id, user_id)`. Un même utilisateur peut avoir plusieurs rôles dans un workspace (Supply Chain Coordinator + membre comité — norme SCI terrain 3-5 personnes).
Voir `DMS_V4.2.0_SCHEMA.sql` table `workspace_memberships`.

**BLOC-04** — Middleware tenant RLS : `SET LOCAL` obligatoire, documenté comme RÈGLE-W01.
Voir `DMS_V4.2.0_INVARIANTS.md` §RÈGLE-W01.

### 3.5 Observations intégrées

**OBS-01** — `procurement_file JSONB` : documenté comme dette planifiée. À terme = vue matérialisée calculée depuis `bundle_documents` et `evaluation_documents`. Migration prévue post-pilote.

**OBS-02** — `workspace_events` partitionnement : documenté comme note d'échelle. Partitionnement par `RANGE(emitted_at)` planifié avant passage multi-tenant (> 10 tenants ou > 500 processus/an).

---

## PARTIE IV — INVARIANTS

Référence complète : `docs/freeze/DMS_V4.2.0_INVARIANTS.md`

Les 9 invariants canon (INV-R1→R9) sont préservés et adaptés au workspace.
Les 8 invariants workspace (INV-W01→W08) sont ajoutés.
La règle RÈGLE-W01 (SET LOCAL tenant obligatoire) est ajoutée.

---

## PARTIE V — RBAC

Référence complète : `docs/freeze/DMS_V4.2.0_RBAC.md`

17 permissions × 6 rôles pilote SCI Mali.
Migration RBAC V4.1.0 → V4.2.0 documentée.

---

## PARTIE VI — SÉQUENCE DE MIGRATION

Référence complète : `docs/freeze/DMS_V4.2.0_MIGRATION_PLAN.md`

Séquence : semaines 0→10, migrations 068→075, script migration données avec BLOC-01 et BLOC-02, migration 074 DROP case_id.

---

## PARTIE VII — STOP SIGNALS

Référence complète : `docs/freeze/DMS_V4.2.0_STOP_SIGNALS.md`

12 signaux d'arrêt avec condition, commande de vérification, action, invariant/règle.

---

## PARTIE VIII — STACK TECHNIQUE

### Nouvelles dépendances (RÈGLE-13 : ADR obligatoire avant premier commit)

| Dépendance | Usage | ADR requis |
|---|---|---|
| `pydantic-ai` | Tools typés Pass -1 | ADR-002 |
| `langgraph` | Orchestration stateful | ADR-003 |
| `pgvector` (extension PG) | Embeddings mémoire W4 | ADR-004 |
| `langfuse` (self-hosted Docker) | Observabilité agent | ADR-005 |

Dépendances existantes dans le canon (pas de nouvel ADR) :
- `mistralai` (Mistral OCR 3 = même provider)
- `azure-ai-formrecognizer` (fallback OCR)

### Pool de connexions

```
PLAN REQUIS : Railway Pro (100 connexions max)

ALLOCATION :
  FastAPI pool        :  10
  ARQ workers (3)     :   3
  LangGraph saver     :   3
  Langfuse PG         :   3
  Marge               :   6
  Total               :  25 / 100
```

### LLM Chain

```
PASS -1 (assemblage) :
  OCR : Mistral OCR 3 → Azure Doc Intel (fallback)
  PDF natif : VLM direct (GPT-4.1 Mini ou Gemini Flash)
  Classification : Mistral Small

M12-M14 (analyse) :
  Inchangé — déterministe + Mistral Small

COMITÉ W3 :
  Pas de LLM. Déterministe. Humain seul.

W4 RAG (post-pilote) :
  Embeddings : BGE-M3 ou Mistral Embed
  Reranking : Mistral Rerank
```

---

## PARTIE IX — MAPPING MILESTONES CANON

| Milestone canon | Satisfait par | Validation |
|---|---|---|
| M16A Submission Registry | Migration 069 (workspace_events type submission_*) | workspace_events tracent les dépôts |
| M16B Committee + Seal | Migration 071 + routes W3 | committee_sessions FSM + PV sealed |
| M17 CBA Gen | Routes W1 évaluation + export | CBA = projection evaluation_documents |
| M18 PV Gen | Seal session → pv_snapshot + export | PV = snapshot JSON + SHA-256 + export formaté |
| M19 Observabilité | Langfuse self-hosted semaine 1 | Tracing + cost + evals |
| M20 Performance Gates | Tests performance semaine 9 | SLA vérifiés en conditions Mopti |
| M21 Déploiement Mali | Pilote semaine 9-10 | 5 processus réels SCI Mali |

---

## PARTIE X — PRINCIPE DIRECTEUR

> **DMS est un Procurement Process Workspace.**
>
> L'unité fondamentale est le `ProcessWorkspace`, pas le document.
> Les bundles fournisseurs, évaluations, sessions de comité, décisions
> et la mémoire marché sont des sous-objets de ce workspace.
>
> Le procurement officer dépose un ZIP et retrouve en 30 secondes
> ses bundles assemblés, ses scores calculés, ses écarts mercuriale signalés.
> Il ne copie plus rien dans Excel. Il ne cherche plus la mercuriale par email.
>
> Le comité délibère dans DMS, pas à côté. Chaque commentaire, chaque
> contestation, chaque clarification est tracée. Le PV est le scellement,
> pas un document Word rédigé après la réunion.
>
> La mémoire marché vit indépendamment des processus. Un procurement officer
> peut interroger les prix du ciment à Mopti sans ouvrir aucun dossier.
> Chaque décision scellée enrichit cette mémoire automatiquement.
>
> Le système ne recommande jamais. Il ne classe jamais. Il ne désigne
> aucun gagnant. Il présente les faits — scores, écarts, flags —
> et l'humain décide.
>
> **Le moat de DMS n'est pas le pipeline. C'est le workspace cumulatif vivant.**
> **L'expérience est le produit. La traçabilité est le moat.**

---

## PARTIE XI — HASHES DE VÉRIFICATION

```
SHA256 fichier  : [GÉNÉRÉ PAR AGENT APRÈS COMMIT]
SHA256 commit   : [GÉNÉRÉ PAR AGENT APRÈS COMMIT]
Date hash       : [GÉNÉRÉE PAR AGENT APRÈS COMMIT]

Commande :
  sha256sum docs/freeze/DMS_V4.2.0_ADDENDUM.md

Ce document est gelé après hash.
Tout amendement → docs/freeze/DMS_V4.2.1_PATCH.md
Ce fichier n'est plus jamais modifié.
```

---

*DMS V4.2.0 ADDENDUM — Workspace-First — Version Opposable Finale*
*BLOC-01 corrigé (whitelist frozenset + assertion)*
*BLOC-02 corrigé (map_status exception explicite)*
*BLOC-03 corrigé (UNIQUE workspace+user+role)*
*BLOC-04 corrigé (RÈGLE-W01 SET LOCAL)*
*OBS-01 intégré (procurement_file = dette planifiée)*
*OBS-02 intégré (partitionnement planifié)*
*Statut : APPROVED — FREEZE DÉFINITIF après hash*
