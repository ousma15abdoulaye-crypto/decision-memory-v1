# CONTEXT ANCHOR OFFICIEL — VERSION OPPOSABLE

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  CONTEXT ANCHOR — DMS v4.1 (RÉDUIT AGENTS IA)                       ║
║  Dernière mise à jour : 2026-04-21                                   ║
║  Railway prod head : 098 (098_primary_admin_email_owner_mandate)     ║
║  Dépôt alembic heads : 098                                           ║
║  Main HEAD : dc975355 (PR #398 MERGÉ)                               ║
║  CTO : Abdoulaye Ousmane                                             ║
║  Statut : DOCUMENT VIVANT — OPPOSABLE                               ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ██████████████████████████████████████████████████████████████    ║
║  ██  CLAUSE D'INTÉGRITÉ MODIFIÉE — 2026-04-21             ██    ║
║  ██████████████████████████████████████████████████████████████    ║
║                                                                      ║
║  ADDENDUM 2026-04-21 — DÉGEL AUTORISÉ PAR CTO SENIOR SENIOR        ║
║    Réduction autorisée pour optimisation agents IA.                 ║
║    Conservation : RÈGLES + ERREURS + ÉTAT ACTUEL + CONTRATS.       ║
║    Suppression : historique détaillé PRs anciennes, logs verbeux.   ║
║                                                                      ║
║  RÈGLE-ANCHOR-01 — INTÉGRITÉ (AMENDÉE 2026-04-21)                  ║
║    Document peut être condensé sur autorisation CTO Senior.         ║
║    Ajouts restent obligatoires pour nouvelles informations.         ║
║    Suppressions tracées par commit avec justification.              ║
║                                                                      ║
║  RÈGLE-ANCHOR-02 — MISE À JOUR OBLIGATOIRE                         ║
║    Ce document DOIT être mis à jour à chaque fin de session.       ║
║    Format : date ISO + contenu + commit sur main.                  ║
║                                                                      ║
║  RÈGLE-ANCHOR-03 — SOURCE DE VÉRITÉ UNIQUE                         ║
║    Ce document prime sur toute mémoire de session du LLM.         ║
║    En cas de doute : ce document a raison, le LLM a tort.         ║
║                                                                      ║
║  RÈGLE-ANCHOR-04 — INTERDICTION D'IMPROVISATION                    ║
║    Le LLM ne peut proposer AUCUNE solution technique               ║
║    non fondée sur ce document ou le Plan Directeur V4.1.          ║
║    Si l'information manque : STOP — demander CTO.                  ║
║                                                                      ║
║  RÈGLE-ANCHOR-05 — ALEMBIC INTOUCHABLE                             ║
║    Migrations existantes = FREEZE ABSOLU.                           ║
║    Toute migration = nouveau fichier séquentiel uniquement.        ║
║    Zéro modification des migrations existantes.                    ║
║    Zéro autogenerate. SQL brut uniquement.                          ║
║                                                                      ║
║  RÈGLE-ANCHOR-06 — RAILWAY PROTÉGÉ                                 ║
║    INTERDIT : migrations, ALTER, DROP, DELETE sur Railway.         ║
║    INTERDIT : modifier services DMS existants.                      ║
║    INTERDIT : SQLite, toute base autre que PostgreSQL.             ║
║    AUTORISÉ : compute, seeds validés CTO, probe, lecture.          ║
║    Flag requis : DMS_ALLOW_RAILWAY=1.                              ║
║                                                                      ║
║  RÈGLE-ANCHOR-07 — STOP EXPLICITE OBLIGATOIRE                      ║
║    Le LLM DOIT s'arrêter et demander CTO si :                      ║
║      - Règle du Plan Directeur absente du contexte                 ║
║      - Action touche Railway, Alembic, ou DB prod                  ║
║      - Deux mandats consécutifs échouent sur le même point        ║
║      - Le LLM commence à improviser faute d'information           ║
║                                                                      ║
║  RÈGLE-ANCHOR-08 — PÉRIMÈTRE FERMÉ OBLIGATOIRE                     ║
║    Tout mandat doit lister exactement les fichiers à créer.       ║
║    Zéro fichier supplémentaire non listé.                          ║
║    L'agent vérifie le périmètre avant tout commit.                ║
║                                                                      ║
║  RÈGLE-ANCHOR-09 — ERREURS CAPITALISÉES PERMANENTES               ║
║    Toute erreur commise est inscrite ici définitivement.           ║
║    Elle sert de garde-fou pour toutes les sessions suivantes.     ║
║                                                                      ║
║  RÈGLE-ANCHOR-10 — HIÉRARCHIE DES AUTORITÉS                       ║
║    1. Plan Directeur DMS V4.1                                      ║
║    2. Ce context anchor                                             ║
║    3. Les mandats CTO                                               ║
║    4. Le LLM (exécutant — zéro autorité propre)                   ║
║    En cas de conflit : l'autorité supérieure prime.                ║
║                                                                      ║
║  ██████████████████████████████████████████████████████████████    ║
║  ██              FIN CLAUSE D'INTÉGRITÉ                       ██    ║
║  ██████████████████████████████████████████████████████████████    ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ÉTAT ACTUEL GIT / ALEMBIC / RAILWAY — 2026-04-21                  ║
║  ──────────────────────────────────────────────────────────────     ║
║  main HEAD           : dc975355 (PR #398 JWT admin merged)          ║
║  alembic dépôt       : 098_primary_admin_email_owner_mandate        ║
║  alembic Railway prod: 098 (aligné dépôt)                           ║
║  RÈGLE              : toute nouvelle migration = 099+ séquentiel     ║
║  Single-head        : OBLIGATOIRE (alembic heads = 1 ligne)         ║
║                                                                      ║
║  SCHÉMAS PostgreSQL — DÉFINITIF                                     ║
║  ──────────────────────────────────────────────────────────────     ║
║  public    : tables métier DMS                                      ║
║  couche_b  : tables procurement                                     ║
║  couche_a  : agent_checkpoints, agent_runs_log                      ║
║  SQLite    : INTERDIT — PostgreSQL uniquement                       ║
║                                                                      ║
║  CONTRACT-02 — RAILWAY                                              ║
║  ──────────────────────────────────────────────────────────────     ║
║  INTERDIT Railway  : migrations, ALTER, DROP, DELETE               ║
║  AUTORISÉ Railway  : compute, seeds validés CTO, probe              ║
║  Flag Railway      : DMS_ALLOW_RAILWAY=1                            ║
║                                                                      ║
║  JOINTURE MERCURIALS — DÉFINITIVE                                   ║
║  ──────────────────────────────────────────────────────────────     ║
║  mercurials.item_id (UUID) = artefact legacy — IGNORÉ              ║
║  Chemin obligatoire :                                                ║
║    item_canonical → mercurials_item_map → dict_item_id             ║
║  Jointure : LOWER(TRIM(item_canonical)) des deux côtés              ║
║                                                                      ║
║  FREEZE ABSOLU — NE JAMAIS MODIFIER                                 ║
║  ──────────────────────────────────────────────────────────────     ║
║  docs/freeze/DMS_V4.1.0_FREEZE.md                                  ║
║  docs/freeze/SYSTEM_CONTRACT.md                                     ║
║  docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md                      ║
║  services/annotation-backend/prompts/schema_validator.py            ║
║  migrations Alembic 001 → 098                                       ║
║                                                                      ║
║  RÈGLES ANNOTATION — FIGÉES                                         ║
║  ──────────────────────────────────────────────────────────────     ║
║  Confiance     : 1.00 / 0.80 / 0.60 UNIQUEMENT (jamais 0.0, 0.9)  ║
║  NOT_APPLICABLE: confidence=1.0 par convention                      ║
║  Valeurs absence: ABSENT | NOT_APPLICABLE | AMBIGUOUS               ║
║  to_name       : "document_text" (backend.py) — jamais "text"       ║
║  Format JSONL  : wrapper ground_truth obligatoire                   ║
║  Statuts       : annotated_validated | review_required | rejected   ║
║                                                                      ║
║  SEUILS M15 — FIGÉS NON NÉGOCIABLES                                 ║
║  ──────────────────────────────────────────────────────────────     ║
║  coverage_extraction  ≥ 80%                                        ║
║  unresolved_rate      ≤ 25%                                         ║
║  vendor_match_rate    ≥ 60%                                        ║
║  review_queue_rate    ≤ 30%                                        ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ERREURS CAPITALISÉES (CONDENSÉES) — NE JAMAIS REPRODUIRE          ║
║  ──────────────────────────────────────────────────────────────     ║
║  E-01  mistralai v1.x : from mistralai import Mistral               ║
║  E-02  Format JSONL : lire Plan Directeur Partie VIII AVANT coder   ║
║  E-03  Confiance : 3 niveaux {0.6, 0.8, 1.0} — jamais 0.0/0.9      ║
║  E-04  RÈGLE-19 : evidence_hint PARTOUT — jamais valeur nue        ║
║  E-10  DJANGO_DB=default force SQLite — INTERDIT                    ║
║  E-12  Chaîne Alembic modifiée sans CTO = faute grave              ║
║  E-13  Context anchor dégradé → perte règles → dégâts projet       ║
║  E-22  text_len seul comme critère OCR — INTERDIT — calibrer       ║
║  E-23  Migration corrective nécessaire si migration en prod défaut  ║
║  E-65  confidence=0.0 dans squelette JSON prompt — Mistral copie    ║
║         NOT_APPLICABLE → confidence=1.0 par convention (LOI 4)      ║
║  E-66  to_name="text" dans backend.py — valeur correcte =           ║
║         "document_text" (match XML Label Studio)                     ║
║  E-67  Implémentation sans mandat CTO émis explicitement            ║
║  E-71  VALID_ALEMBIC_HEADS whitelist : ajouter chaque migration     ║
║         dans tests/test_046b_imc_map_fix.py                         ║
║  E-82  Sources vérité Alembic non MAJ après merge migration        ║
║  E-99  MQL asyncpg : (?<!:):([a-zA-Z_]\w*) évite ::text KeyError   ║
║  E-100 Settings V5.2 : MISTRAL_API_KEY required, cache_clear tests  ║
║  E-101 RLS tenant : app.current_tenant (pas seulement app.tenant_id)║
║  E-103 Prometheus : pas workspace_id UUID label (cardinalité)       ║
║                                                                      ║
║  KILL LIST — REJET IMMÉDIAT AGENT                                   ║
║  ──────────────────────────────────────────────────────────────     ║
║  ❌ confidence hors {0.6, 0.8, 1.0}                                 ║
║  ❌ confidence=0.0 dans squelette JSON prompt                        ║
║  ❌ to_name="text" dans backend.py (correct: "document_text")       ║
║  ❌ null libre hors ABSENT/NOT_APPLICABLE/AMBIGUOUS                 ║
║  ❌ text_len seul comme critère OCR                                  ║
║  ❌ statut "validated" seul (correct: "annotated_validated")        ║
║  ❌ schema_validator.py modifié sans GO CTO explicite               ║
║  ❌ winner/rank/recommendation/best_offer (RÈGLE-09 V4.1.0)         ║
║  ❌ implémentation sans mandat CTO émis explicitement               ║
║  ❌ git push origin main (commits directs sur main)                 ║
║  ❌ gh pr merge --admin ou merge avant CI verte                     ║
║  ❌ git add . (toujours fichier explicite)                          ║
║  ❌ fichier hors périmètre modifié sans GO CTO                      ║
║                                                                      ║
║  PROTOCOLE FIN DE SESSION — OBLIGATOIRE                             ║
║  ──────────────────────────────────────────────────────────────     ║
║  1. Mettre à jour ce fichier si nouveaux apprentissages            ║
║  2. Capitaliser toute nouvelle erreur dans E-XX                     ║
║  3. Commit message : "docs(anchor): session YYYY-MM-DD"            ║
║                                                                      ║
║  PROTOCOLE DÉBUT DE SESSION — OBLIGATOIRE                           ║
║  ──────────────────────────────────────────────────────────────     ║
║  1. CTO colle ce fichier en début de session                        ║
║  2. LLM confirme lecture complète                                   ║
║  3. LLM liste les règles applicables à la session                  ║
║  4. Zéro action avant cette confirmation                           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## CHANGELOG RÉDUCTION 2026-04-21

**Autorisation** : CTO Senior Senior (Abdoulaye Ousmane)  
**Justification** : Optimisation agents IA — suppression verbosité historique

**Conservé** :
- Les 10 RÈGLES ANCHOR (01-10)
- ERREURS CAPITALISÉES condensées (E-01 à E-103, 20 les plus critiques)
- KILL LIST complète
- État actuel git/alembic/Railway
- Contrats essentiels (Railway, jointures, freeze absolus)
- Protocoles session début/fin
- Seuils M15

**Supprimé** :
- Addendums détaillés PRs anciennes (~70% du document)
- Historique complet migrations (gardé état actuel seulement)
- Logs Railway détaillés ligne par ligne
- Milestones historiques détaillés
- Données métier exhaustives (gardé structure critique)

**Réduction** : ~3500 lignes → ~250 lignes (93% réduction)

---

**FIN CONTEXT ANCHOR RÉDUIT**
