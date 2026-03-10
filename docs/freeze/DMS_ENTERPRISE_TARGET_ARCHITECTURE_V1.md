# DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1
# PLAN DIRECTEUR ARCHITECTURE CIBLE
# Statut    : FREEZE DÉFINITIF
# Date      : 2026-03-10
# Décideur  : AO — Abdoulaye Ousmane
# Supérieur à : tout mandat, toute décision agent implicite
# Amendable : uniquement par ADR-META signé AO
#             processus défini dans ADR-META-001-AMENDMENT-PROCESS.md

---

## 0. HIÉRARCHIE DE LECTURE OBLIGATOIRE

Ordre exact. Sans exception. Sans raccourci.

  0. docs/freeze/SYSTEM_CONTRACT.md              ← couche zéro
  1. docs/freeze/DMS_V4.1.0_FREEZE.md
  2. docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md
  3. docs/freeze/DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.md
  4. docs/freeze/DMS_MRD_PLAN_V1.md
  5. docs/freeze/MRD_CURRENT_STATE.md
  6. docs/freeze/BASELINE_MRD_PRE_REBUILD.md
  7. mandat du milestone en cours

Règle conflit inter-couches :
  CONFLIT   : couche N dit X, couche N+1 dit NOT-X
              → couche supérieure gagne, toujours, sans exception
  SILENCE   : couche N silencieuse, couche N+1 traite
              → couche N+1 s'applique, pas de conflit
  AMBIGUÏTÉ : couche N interprétable dans deux sens ou plus
              → STOP immédiat. Poster au CTO.
              L'agent ne tranche jamais.

Ce document complète le canon existant.
Il n'autorise aucune dérive hors V4 / Framework / MRD_PLAN.

---

## 1. BUT

Fixer l'architecture cible de DMS pour éviter :

  - dérive mono-tenant implicite
  - refonte future coûteuse
  - patches successifs sur schéma trop petit
  - agents qui inventent une architecture
    au fil des milestones

Ce document n'impose pas d'implémenter toute
l'architecture cible immédiatement.
Il impose que tout build nouveau soit compatible
avec elle.
La Section 15 dit exactement ce qui s'applique quand.
Un agent sans Section 15 ne peut pas décider seul.

---

## 2. POSITIONNEMENT PRODUIT

DMS est conçu pour servir :

  - organisations à volume faible ou moyen
  - grandes ONG
  - administrations publiques
  - mines et groupes industriels
  - structures multi-entités / multi-pays

Conséquences architecturales non négociables :

  DMS ne doit pas être conçu comme outil
  mono-client fragile.
  DMS doit être tenant-ready by design.
  DMS doit rester audit-proof.
  DMS doit préserver un génome canonique stable.
  Toute décision qui ferme une de ces trajectoires
  est interdite sans ADR-META signé AO.

---

## 3. TROIS CLASSES DE DONNÉES

Toute donnée dans DMS appartient à exactement
une classe. Pas deux. Pas "à peu près".
La classification est obligatoire et opposable.

### 3.1 GLOBAL_CORE

Données canoniques globales du système.
Elles portent le génome commun.
Partagées entre tous les tenants.
Aucun tenant ne les possède.

  Exemples confirmés :
    item_uid, fingerprint, item_code
    label_fr, label_status
    taxo_l1, taxo_l2, taxo_l3, taxo_version
    dict_collision_log (global)
    normalize() et ses vecteurs
    units, geo_master, procurement_categories
    procurement_dict_items, procurement_dict_aliases
    market_signals (voir note ci-dessous)

  Note market_signals :
    Classé GLOBAL_CORE.
    La dimension géographique est portée par
    zone_id nullable — dimension d'analyse,
    pas frontière tenant.
    Décision de granularité définitive reportée
    à M9 quand formule V1.0 implémentée.
    Si M9 révèle besoin différent → ADR-META à M9.

  Règles absolues :
    org_id absent — jamais sur une table GLOBAL_CORE.
    Pas de duplication naïve par tenant.
    Pas de fragmentation du génome.
    Aucune logique locale ne casse l'identité
    canonique.

### 3.2 TENANT_SCOPED

Données propres à une organisation.
Elles n'ont de sens que dans le contexte
d'un tenant précis.

  Exemples confirmés :
    cases, documents, offers
    evaluation_criteria, score_history
    committees, submission_registries
    market_surveys (enquête terrain propre à l'org)
    decision_history (décisions propres)
    annotation_registry (corpus propre)
    vendors (liste propre à l'org)
    extraction_jobs, offer_extractions
    elimination_log

  Règles absolues :
    org_id obligatoire dans le schéma dès création.
    Préparé nullable avant M14 (bootstrap schéma).
    Obligation applicative immédiate : zéro insertion
    avec org_id=NULL dans le code — avant même M14.
    RLS obligatoire activé à M14.
    Audit trail tenant-scoped obligatoire.

### 3.3 TENANT_OVERLAY

Couche de surcouche locale sur le registre global.
Un overlay enrichit, qualifie, mappe.
Il ne remplace jamais le génome.

  Exemples :
    alias locaux sur item canonique
    validation locale d'un item global
    mapping taxonomique local
    statut local d'usage
    override non destructif
    file de review locale

  Règles absolues :
    Un overlay ne modifie jamais l'identité canonique.
    Identifiant obligatoire de tout overlay :
      (item_uid, org_id, overlay_type)
    Zéro overlay anonyme.
    RLS obligatoire activé à M14.

  Règle de résolution overlay vs canonical :
    Si overlay entre en conflit avec canonical :
      → overlay marqué conflict_flag = TRUE
      → canonical prend toujours la précédence
      → résolution manuelle via proposal uniquement
      → jamais résolution automatique
      → jamais silencieux

  Règle cascade deprecated :
    Si item canonical passe label_status = deprecated :
      → tous les overlays liés marqués
        orphan_flag = TRUE automatiquement
      → entrée automatique en review queue
      → jamais suppression silencieuse des overlays
      → jamais activation automatique d'un overlay
        orphelin
      → résolution humaine obligatoire

---

## 4. RÈGLE OBLIGATOIRE DE CLASSIFICATION

Toute nouvelle table créée à partir de maintenant
doit être classée explicitement.

La classification doit apparaître dans :
  - le mandat (BLOC 3 — liste des tables)
  - la migration (commentaire sur CREATE TABLE)
  - le résultat de milestone (MRDX_RESULT.md)
  - tout ADR de schéma concerné

Format obligatoire dans toute migration :

  -- CLASSIFICATION : GLOBAL_CORE
  -- CLASSIFICATION : TENANT_SCOPED
  -- CLASSIFICATION : TENANT_OVERLAY

Aucune table nouvelle sans classification.
Absence = STOP avant merge.

Règle par défaut si doute :
  Doute sur la classification
  → TENANT_SCOPED par défaut
  → org_id préparé nullable
  → décision CTO dans BLOC 10 du mandat
  L'agent ne décide pas seul d'une classification
  ambiguë.

---

## 5. RLS ET MULTI-TENANT

### 5.1 Principe

DMS est multi-tenant target by design.
Ce n'est pas une option future.
C'est une contrainte de conception présente.

### 5.2 Règle d'application RLS

  GLOBAL_CORE    : RLS non applicable
                   données système partagées
  TENANT_SCOPED  : RLS obligatoire — actif M14
  TENANT_OVERLAY : RLS obligatoire — actif M14

### 5.3 Interdiction absolue

Il est interdit d'appliquer la règle simpliste :
  "toute requête doit contenir org_id"
Cette règle est fausse et dangereuse sur GLOBAL_CORE.

### 5.4 Préparation org_id — règle précise et opposable

  Avant M14 — obligation schéma :
    org_id TEXT nullable dans toute migration
    TENANT_SCOPED ou TENANT_OVERLAY.
    La DB accepte NULL = filet schéma uniquement.

  Avant M14 — obligation applicative immédiate :
    Toute insertion sur table TENANT_SCOPED
    ou TENANT_OVERLAY doit porter org_id non null
    dans le code applicatif.
    Zéro insertion org_id=NULL dans le code.
    Vérifiable par CB-01 SEMANTIC_GUARD V2.
    Violation = bug critique — pas un warning.

  À M14 :
    ALTER COLUMN org_id SET NOT NULL sur toutes
    les tables TENANT_SCOPED et TENANT_OVERLAY.
    RLS activé sur ces mêmes tables.
    Migration dédiée avec cycle CB-04 complet.

---

## 6. GÉNOME CANONIQUE — RÈGLES FIGÉES ET OPPOSABLES

Les éléments suivants constituent le génome stable.
Ils sont protégés par triggers, tests et guards.
Toute modification sans ADR-META = violation critique.

  item_uid
    → immuable après INSERT
    → protégé par trg_protect_item_identity
    → test CB-02 obligatoire

  fingerprint
    → immuable après initialisation
    → sha256(normalize(label_fr)|source_type)
    → protégé par trg_protect_item_identity
    → test CB-02 obligatoire

  item_code
    → immuable après initialisation
    → format LG-YYYYMM-NNNNNN
    → protégé par trg_protect_item_identity [IS-10]
    → test CB-02 obligatoire

  normalize()
    → gelé : strip + lower + collapse_whitespace
    → vecteurs de test immuables dans tests/
    → toute modification = STOP global
      + audit obligatoire (CB-07)
      + emergency track ADR-META si en production

  label_fr
    → immuable si label_status = validated
    → protégé par trg_protect_item_identity [BRIQUE-2]
    → correction orthographique → alias, jamais UPDATE

  label_status
    → draft | validated | deprecated
    → deprecated = irréversible
    → cascade orphan_flag sur overlays liés

  taxonomie (taxo_l1/l2/l3/version)
    → dérivée après registre — jamais avant
    → INV-07 DMS_ORCHESTRATION_FRAMEWORK_V1.md
    → RÈGLE-29 DMS_V4.1.0_FREEZE.md

  collision log
    → append-only — trigger trg_collision_log_append_only
    → jamais muté hors champs status et resolved_*

Règle agent sur le génome :
  Avant migration touchant le génome :
    vérifier triggers de protection présents
  Après migration :
    re-vérifier triggers de protection présents
  Test de non-régression obligatoire dans le milestone.

---

## 7. CIRCUIT BREAKERS

Les CB sont les gardiens automatiques du système.
Chaque CB a un statut opposable, un milestone
d'activation et un owner.

### Tableau de statut CB

| CB    | Nom                     | Statut      | Milestone | Owner  |
|-------|-------------------------|-------------|-----------|--------|
| CB-01 | SEMANTIC_GUARD          | PLANNED     | M8/M9     | Agent  |
| CB-02 | INVARIANT_TEST_SUITE    | PARTIEL     | M9        | Agent  |
| CB-03 | BASELINE_PARITY_CHECK   | PARTIEL     | M9        | Agent  |
| CB-04 | MIGRATION_ROLLBACK_GATE | ACTIF ✓     | MRD-4     | Agent  |
| CB-05 | CONSTRAINT_HEADER       | PLANNED     | M8        | CTO    |
| CB-06 | AGENT_PERF_LOG          | NOT_STARTED | M10A      | CTO    |
| CB-07 | NORMALIZE_IMMUTABILITY  | NOT_STARTED | M9        | Agent  |
| CB-08 | COLLISION_TRIAGE_RULE   | PARTIEL     | M8        | CTO    |

Légende statut :
  ACTIF        : vérifiable et vrai en prod maintenant
  PARTIEL      : base existe — compléter au milestone
  PLANNED      : à créer au milestone indiqué
  NOT_STARTED  : hors scope immédiat

### CB-01 — SEMANTIC_GUARD

  Objet :
    Bloquer le code agent sémantiquement faux
    avant merge.

  V1 (M8) vérifie :
    colonnes autorisées / interdites
    patterns interdits : DELETE+INSERT registre,
    downgrade() absent, down_revision absent,
    DATABASE_URL contenant railway dans scripts locaux,
    fichiers hors périmètre mandat

  V2 (M9) ajoute :
    routing table : table → classe
    GLOBAL_CORE   : org_id absent = correct
    TENANT_SCOPED : org_id absent dans INSERT = alerte
    TENANT_OVERLAY: org_id absent dans INSERT = alerte

### CB-02 — INVARIANT_TEST_SUITE

  Objet :
    Convertir tous les invariants DMS en tests
    exécutables.

  Minimum obligatoire à M9 :
    item_uid immuable
    fingerprint immuable après initialisation
    item_code immuable
    normalize() sortie exacte sur vecteurs figés
    taxonomie après registre
    alembic heads = 1 ligne exacte
    audit trigger présent sur dict_items
    append-only collision log
    label_status deprecated irréversible

### CB-03 — BASELINE_PARITY_CHECK

  Objet :
    Comparer local et Railway avant milestone
    critique.

  Minimum :
    alembic head local vs Railway
    counts critiques (dict_items, aliases, vendors)
    triggers critiques présents
    hash global registre selon périmètre documenté

  Statuts :
    PASS  : tout aligné
    DRIFT : divergence documentée — continuer avec note
    SPLIT : divergence critique → STOP immédiat

### CB-04 — MIGRATION_ROLLBACK_GATE (ACTIF depuis MRD-4)

  Objet :
    Interdire toute migration non rollbackable.

  Cycle obligatoire sans exception :
    1. upgrade → assert état cible
    2. downgrade → assert état initial
    3. re-upgrade → assert final
  Sans cycle complet : migration NOT DONE.
  C'est non négociable.

### CB-05 — CONSTRAINT_HEADER

  Objet :
    Mettre les contraintes vitales dans les
    200 premiers tokens de tout mandat.

  Actif dès M8 — tout mandat futur commence par :
    invariants critiques applicables au milestone
    patterns interdits
    hors-scope absolu
    règle STOP du milestone

  Pas de prose. Pas de rappel de contexte.
  Contraintes uniquement.

### CB-06 — AGENT_PERF_LOG

  Objet :
    Tracer le comportement réel des agents
    pour calibrer le routing de modèles.

  Champs minimum :
    session, date, modèle, type de tâche
    erreurs détectées, corrections apportées, verdict

  Destination : docs/audits/AGENT_PERF_LOG.md
  Alimenté par le CTO après chaque milestone.

### CB-07 — NORMALIZE_IMMUTABILITY_TEST

  Objet :
    Sanctuariser normalize() comme élément
    constitutionnel du génome.

  Exigences :
    Vecteurs de test figés dans tests/
    Sortie exacte vérifiée à chaque CI
    Toute modification de normalize() :
      → STOP global
      → audit obligatoire
      → si en production : emergency track ADR-META

### CB-08 — COLLISION_TRIAGE_RULE

  Objet :
    Éviter une queue de collisions morte.

  610 collisions pending → triage obligatoire M8.

  Triage :
    TIER-1 : score >= 95  → batch-review prioritaire
    TIER-2 : score 85-94  → revue assistée
    TIER-3 : cas ambigus  → revue experte

  Interdit : auto-merge silencieux.
  Autorisé : validation humaine en batch.
  Queue sans triage après M8 = dette bloquante M9.

---

## 8. DRAFT GOVERNANCE

  stale_draft_days  : 90 jours
  Configurable      : par organisation, pas par agent
  Qui définit       : CTO (central) | org (tenant)
  Au-delà du seuil  : review via taxo_proposals_v2
                      jamais validation automatique
                      jamais mutation silencieuse

  Cas particulier corpus initial DMS :
    1490 items label_status=draft = seeds registre
    = legacy_draft = non soumis au seuil avant M10
    Validation progressive humaine item par item.

---

## 9. AMENDMENT PROCESS

Tout amendement à ce document suit ADR-META-001.
Fichier : docs/freeze/ADR-META-001-AMENDMENT-PROCESS.md

Ce document n'est jamais modifié en place.
Patch  → DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.1_PATCH.md
V2     → DMS_ENTERPRISE_TARGET_ARCHITECTURE_V2.md
Signal de validation unique :
  Présence dans FREEZE_HASHES.md = validé par AO.
  Absent de FREEZE_HASHES.md = non applicable.

---

## 10. RÈGLES DE BUILD

### 10.1 Classification obligatoire
  Aucune table sans GLOBAL_CORE | TENANT_SCOPED
  | TENANT_OVERLAY.
  Doute → TENANT_SCOPED par défaut.
  Décision CTO dans BLOC 10 si ambiguïté.

### 10.2 Génome protégé
  Aucune nouvelle logique d'identité hors Section 6.
  Toute touche au génome → Q9 checklist obligatoire.

### 10.3 Compatibilité multi-tenant
  org_id préparé nullable sur toute table
  TENANT_SCOPED dès sa création.
  Obligation applicative : zéro insertion NULL.
  À M14 : NOT NULL + RLS.

### 10.4 Règle d'enforceur
  Toute règle critique doit avoir AU MOINS UN
  enforceur dans le code : test, trigger, guard
  ou migration.
  La documentation seule ne suffit pas.
  Règle non enforcée en code = dette technique
  prioritaire au milestone suivant.

### 10.5 Architecture explicite
  Aucun agent ne décide d'une architecture
  future implicite.
  Toute cible future doit être écrite et gelée.

---

## 11. CE QUI N'EST PAS IMPOSÉ IMMÉDIATEMENT

  RLS sur toutes les tables
  org_id NOT NULL sur tout le schéma
  partitioning collision log
  couche réglementaire export IGF
  multi-tenant complet déployé
  hiérarchie résolution overlay (→ M14)
  volumétrie / partitioning (→ quand nécessaire)
  observabilité agent mature (→ M10A)

Mais le build courant ne ferme aucune
de ces trajectoires.

---

## 12. CHECKLIST DE CONFORMITÉ ARCHITECTURALE

Tout milestone répond explicitement à ces 9 questions.
Une réponse manquante = STOP avant merge.

  Q1  Classification table : GLOBAL_CORE
      | TENANT_SCOPED | TENANT_OVERLAY ?

  Q2  Touche-t-on au génome canonique ?

  Q3  Circuit breaker à créer ou mettre à jour ?

  Q4  Parity local/Railway documentée ?

  Q5  Migration rollbackable — CB-04 cycle complet ?

  Q6  Logique compatible multi-tenant ?

  Q7  Risque dette collisions / drafts / taxonomie ?

  Q8  Si TENANT_SCOPED ou OVERLAY :
      org_id préparé nullable ET obligation
      applicative zéro NULL documentée dans le code ?

  Q9  Si touche génome Section 6 :
      trigger de protection vérifié avant
      ET après migration ?

---

## 13. DEUX AXES SIMULTANÉS

### Axe 1 — Exécution immédiate
  Build réel aligné V4 + MRD + Framework + Contract.
  Section 15 dit exactement ce qui s'applique quand.

### Axe 2 — Cap cible
  Architecture enterprise préparée dès maintenant.
  multi-tenant, RLS, overlay model,
  auditabilité lourde, scalabilité gros volumes.

Aucun des deux axes ne doit détruire l'autre.
Quand ils semblent en conflit → STOP. Poster au CTO.

---

## 14. PRINCIPE DIRECTEUR

Critère de dernier recours :

  "Est-ce que cette action reflète exactement
   le réel ou le construit ?"

  Si construit → ne pas faire. Poster au CTO.

  DMS part du réel. Construit sur le réel.
  Mesure contre le réel.
  Chaque agent exécute. Le CTO décide.
  L'architecture est un cap. Le génome est stable.
  Le build d'aujourd'hui ne doit pas hypothéquer
  le déploiement de demain.

---

## 15. TABLE DE DÉCISION PAR MILESTONE

Réponse opérationnelle exacte.
Pas d'interprétation possible.
Un agent qui lit Section 15 sait exactement
ce qu'il fait — et ce qu'il ne fait pas.

Légende :
  MAINTENANT : obligatoire dans ce milestone
  PRÉPARER   : champ dans schéma, logique inactive
  REPORTER   : hors scope — ne pas faire

Règle par défaut milestones non listés explicitement :
  Toute table nouvelle = TENANT_SCOPED par défaut
  org_id préparé nullable
  Obligation applicative zéro NULL
  Décision CTO dans BLOC 10 du mandat

---

### M8 — MARKET SURVEY

  market_surveys             : TENANT_SCOPED MAINTENANT
  org_id migration           : PRÉPARER nullable
  Obligation applicative     : zéro NULL org_id code
  RLS                        : REPORTER
  CB-01 SEMANTIC_GUARD V1    : MAINTENANT
  CB-05 CONSTRAINT_HEADER    : MAINTENANT actif dès M8
  CB-08 COLLISION_TRIAGE     : MAINTENANT trier 610
  Génome                     : non touché N/A

---

### M9 — MARKET SIGNAL

  market_signals             : GLOBAL_CORE MAINTENANT
  org_id                     : REPORTER signal global
  Décision granularité géo   : arbitrer via ADR si besoin
  CB-01 SEMANTIC_GUARD V2    : MAINTENANT routing table
  CB-02 INVARIANT_TEST_SUITE : MAINTENANT version complète
  CB-03 BASELINE_PARITY      : MAINTENANT version M9
  CB-07 NORMALIZE_IMMUTABILITY: MAINTENANT vecteurs figés
  formula_version            : gravée immuable après M9

---

### M10A — GATEWAY STACK

  tables extraction          : TENANT_SCOPED MAINTENANT
  org_id migrations          : PRÉPARER nullable
  Obligation applicative     : zéro NULL org_id
  CB-06 AGENT_PERF_LOG       : MAINTENANT

---

### M10B — GATEWAY CALIBRATION

  annotation_registry        : TENANT_SCOPED MAINTENANT
  org_id                     : PRÉPARER nullable
  CB-02                      : COMPLÉTER corpus annoté

---

### M11 — INGESTION RÉELLE

  offer_extractions          : TENANT_SCOPED MAINTENANT
  org_id                     : PRÉPARER nullable
  Génome normalization        : TOUCHÉ
  CB-07 NORMALIZE_IMMUTABILITY: VÉRIFIER avant merge
  Q9 checklist               : OBLIGATOIRE

---

### M12 — PROCEDURE RECOGNIZER

  tables nouvelles           : TENANT_SCOPED par défaut
  org_id                     : PRÉPARER nullable
  CB-01 SEMANTIC_GUARD       : ACTIF — vérifier patterns
  Génome                     : non touché sauf preuve N/A

---

### M13 — PROFILES SCI + DGMP

  tables nouvelles           : TENANT_SCOPED par défaut
  org_id                     : PRÉPARER nullable
  CB-01                      : ACTIF — vérifier patterns
  Génome                     : non touché N/A

---

### M14 — EVALUATION ENGINE

  RLS                        : ACTIVER TENANT_SCOPED
  org_id                     : SET NOT NULL toutes tables
  CB-01 SEMANTIC_GUARD V2    : VÉRIFIER routing complet
  CB-02 INVARIANT_TEST_SUITE : version complète multi-t
  CB-03 BASELINE_PARITY      : version complète multi-t
  Migration dédiée RLS       : CB-04 cycle complet

---

### M15 — PIPELINE E2E 100 DOSSIERS

  tables nouvelles           : TENANT_SCOPED par défaut
  org_id                     : NOT NULL (RLS actif M14)
  CB-01→CB-04                : tous ACTIFS vérifiés
  Métriques V4 Partie XI     : obligatoires

---

### M16A — SUBMISSION REGISTRY

  submission_registry        : TENANT_SCOPED MAINTENANT
  org_id                     : NOT NULL (RLS actif M14)
  INV-R1→INV-R9 Framework    : tous vérifiés

---

### M16B — COMMITTEE + SEAL

  committees                 : TENANT_SCOPED MAINTENANT
  org_id                     : NOT NULL
  CB-01→CB-04                : tous ACTIFS

---

### M21 — DÉPLOIEMENT MALI

  RLS                        : ACTIF toutes TENANT_*
  Multi-tenant               : ACTIF
  CB-01→CB-08                : tous ACTIFS
  Génome canonique           : audit complet avant deploy
  CONTEXT_ANCHOR             : version finale mise à jour

---

## 16. CHECKSUMS

  SHA256 : [GÉNÉRÉ APRÈS COMMIT]
  Date   : [GÉNÉRÉE APRÈS COMMIT]

  sha256sum \
    docs/freeze/DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.md

  Tout amendement → ADR-META signé AO
                  → patch ou V2 selon ADR-META-001
  Ce fichier n'est plus jamais modifié après hash.
