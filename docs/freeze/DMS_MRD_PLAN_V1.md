# DMS_MRD_PLAN_V1
# PLAN DIRECTEUR REDRESSEMENT DICTIONNAIRE M4→M7
# Statut    : FREEZE DÉFINITIF
# Date      : 2026-03-08
# Décideur  : AO — Abdoulaye Ousmane
# Supérieur à tout plan, mandat ou décision antérieure sur M4→M7
# Amendable : uniquement par DMS_MRD_PLAN_V1.1_PATCH.md signé AO

---

## SECTION 0 — HIÉRARCHIE DE LECTURE

Ordre exact. Sans exception. Sans raccourci.

  0. docs/freeze/SYSTEM_CONTRACT.md
  1. docs/freeze/DMS_V4.1.0_FREEZE.md
  2. docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md
  3. docs/freeze/DMS_MRD_PLAN_V1.md
  4. docs/freeze/MRD_CURRENT_STATE.md
  5. docs/freeze/BASELINE_MRD_PRE_REBUILD.md
  6. mandat du milestone en cours

Conflit inter-couches :
  CONFLIT   : couche N dit X, couche N+1 dit NOT-X → couche N gagne
  SILENCE   : couche N silencieuse, couche N+1 traite → N+1 s'applique
  AMBIGUÏTÉ : → STOP. Poster au CTO. L'agent ne tranche jamais.

---

## SECTION 1 — CONTEXTE ET DIAGNOSTIC

Dernier point sûr           : m6_dictionary_build
Première corruption causale : m7_2_taxonomy_reset
Segment suspect             : m7_2 + m7_3 + m7_4a
Segment conservable         : M4, M5, M6, m7_3b
MRD-3 mergé avec défaillances DEF-MRD3-01 à DEF-MRD3-06
  Corrigées dans MRD-4 — voir Section 1.3

### Défaillances MRD-3

  DEF-MRD3-01 : numéro migration délégué CTO — corrigé MRD-4
  DEF-MRD3-02 : cycle test sans alembic current — corrigé MRD-4
  DEF-MRD3-03 : downgrade() sans fail-loud — corrigé MRD-4
  DEF-MRD3-04 : test alembic_head DB seul pas repo — corrigé MRD-4
  DEF-MRD3-05 : colonne fingerprint absente — corrigé MRD-4
  DEF-MRD3-06 : trigger protection delete absent — corrigé MRD-4

---

## SECTION 2 — OBJECTIF

  Sources réelles entrent tôt
  Dictionnaire = registre canonique vivant
  Identité item stable et indépendante
  Taxonomie dérivée, jamais imposée
  M7 = enrichissement uniquement

---

## SECTION 3 — INVARIANTS

  INV-01  Séquence : M5 brut → M6 canonique → M7 enrichissement
  INV-02  Donnée entre telle qu'elle est. Système s'adapte.
  INV-03  Item existe indépendamment de toute taxonomie
  INV-04  Identité item indépendante : ordre SQL, batch, LLM, taxo
  INV-05  Rebuild = UPSERT fingerprint. Jamais DELETE+INSERT.
  INV-06  Aucun script destructif sans verrou + baseline snapshot
  INV-07  1 migration = 1 downgrade() réel testé avec fail-loud
  INV-08  alembic heads = 1 ligne. heads repo = current DB.
  INV-09  1 milestone = 1 branche = 1 PR = 1 merge = 1 tag
  INV-10  Railway ↔ local : table diff postée avant tout rebuild
  INV-11  Taxonomie = conséquence du registre. Jamais son socle.
  INV-12  LLM ne décide jamais seul. Liste fermée obligatoire.
  INV-13  ON DELETE CASCADE interdit sur tables mémoire terrain

### Définitions opérationnelles

  fingerprint = sha256(normalize(label)+"|"+source_type+"|"+source_id)
  normalize() = strip + lower + collapse_whitespace

  item canonique  = unité registre identifiée par fingerprint stable
  registre        = append-only + UPSERT fingerprint
  alias           = mémoire libellé terrain, préservé à vie
  collision       = même fingerprint deux sources → tracée
  proposal        = suggestion — validation humaine obligatoire
  taxonomie       = couche dérivée versionnée post-registre
  birth_source    = mercuriale | imc | seed
  birth_run_id    = UUID script
  birth_timestamp = now() UTC à l'INSERT

  Déprécier doctrine ≠ supprimer migration.
  Migrations Alembic = append-only. Jamais supprimées.

### Variables d'environnement

  DATABASE_URL         → local uniquement
  RAILWAY_DATABASE_URL → Railway lecture seule
  Guard obligatoire tout script :
    if 'railway' in os.environ.get('DATABASE_URL','').lower():
        raise SystemExit('CONTRACT-02 VIOLÉ')

---

## SECTION 4 — FICHIER D'ÉTAT COURANT

  docs/freeze/MRD_CURRENT_STATE.md
  Mis à jour uniquement par AO après chaque merge.
  Jamais par un agent.
  Contient : last_completed, next_milestone, alignement stack,
             défaillances MRD-3, STOPs actifs, hash chain status.

---

## SECTION 5 — SÉQUENCE MILESTONES

  PRE0 → MRD-0 → MRD-1 → MRD-2 → MRD-4 → MRD-5 → MRD-6

  Ordre figé. Aucun saut. Aucun parallélisme.

---

### MRD-0 — SENTENCE + FREEZE + HASH CHAIN

Nature  : doc pur. Code interdit. DB interdite.
Branche : feat/mrd-0-sentence-freeze

Livrables :
  docs/freeze/DMS_MRD_PLAN_V1.md
  docs/freeze/FREEZE_HASHES.md (mis à jour)
  docs/adr/ADR-MRD0-GOVERNANCE.md
  docs/audits/MRD0_SENTENCE_CTO.md
  docs/freeze/BASELINE_MRD_PRE_REBUILD.md (complétée)

Done binaire :
  [ ] validate_mrd_state.py exit(0)
  [ ] DMS_MRD_PLAN_V1.md commité dans docs/freeze/
  [ ] FREEZE_HASHES.md : 4 hashes réels (V4, Framework, Contract, Plan)
  [ ] validate_mrd_state.py vérifie les 4 hashes à chaque session
  [ ] BASELINE zéro [N] manquant
  [ ] ADR-MRD0-GOVERNANCE.md créé
  [ ] MRD0_SENTENCE_CTO.md créé avec SHA256 réels
  [ ] diff = exactement 5 fichiers
  [ ] PR créée sur GitHub
  [ ] tag mrd-0-done posé par CTO post-merge

---

### MRD-1 — VÉRITÉ REPO + BASELINE

Nature  : diagnostic + nettoyage git
Code    : interdit. DB : lecture seule.

Done binaire :
  [ ] validate_mrd_state.py exit(0)
  [ ] git status propre
  [ ] 1 head Alembic confirmé
  [ ] branches orphelines traitées
  [ ] BASELINE complète
  [ ] tag mrd-1-done

---

### MRD-2 — ADR GÉNÉTIQUE + TESTS CONTRAT

Nature  : ADR + tests — zéro migration.

Done binaire :
  [ ] ADR 8 définitions + 8 interdits IS-01/IS-08
  [ ] Section défaillances MRD-3 dans ADR
  [ ] 5 tests de contrat créés
  [ ] 2 tests intentionnellement rouges documentés
  [ ] tag mrd-2-done

---

### MRD-4 — HARDENING + REBUILD CANONIQUE

Nature  : migration + pipeline rebuild.
Corrige : DEF-MRD3-01 à DEF-MRD3-06.

Done binaire :
  [ ] validate_mrd_state.py exit(0)
  [ ] colonne fingerprint créée
  [ ] trigger protect_item_with_aliases créé
  [ ] trigger protect_item_identity créé
  [ ] downgrade() fail-loud testé
  [ ] pipeline rebuild verdict PASS
  [ ] alias_preservation_rate >= 0.99
  [ ] duplicate_identity = 0
  [ ] destructive_loss = 0
  [ ] tag mrd-4-done

---

### MRD-5 — IDENTITÉ CANONIQUE V1

Done binaire :
  [ ] trigger immuabilité item_uid + fingerprint
  [ ] backfill documenté
  [ ] identity_collision = 0
  [ ] tag mrd-5-done

---

### MRD-6 — TAXONOMIE DÉRIVÉE + M7 RECADRÉ

Done binaire :
  [ ] coverage_gate >= 0.85
  [ ] M7 limité enrichissement dans le code
  [ ] tag mrd-6-done

---

## SECTION 6 — VERDICTS COMPOSANTS

| Composant                          | Verdict                                   |
|------------------------------------|-------------------------------------------|
| vendors M4                         | CONSERVER                                 |
| mercuriale ingest M5               | CONSERVER                                 |
| dict M6 m6_dictionary_build        | CONSERVER — dernier point sûr             |
| aliases sains                      | CONSERVER — préservés à vie               |
| m7_3b_deprecate_legacy_families    | CONSERVER                                 |
| m7_4_dict_vivant                   | CONSERVER                                 |
| m7_2_taxonomy_reset                | FIGER — migration intacte lecture seule   |
| m7_3_dict_nerve_center             | FIGER — migration intacte lecture seule   |
| colonnes structurelles M7          | FIGER                                     |
| m7_4a_item_identity_doctrine       | DOCTRINE DÉPRÉCIÉE — migration intacte    |
| taxonomie imposée comme socle      | DOCTRINE DÉPRÉCIÉE                        |
| m7_rebuild_t0_purge.py             | INTERDIT — CI fail si modifié             |
| tout script DELETE+INSERT registre | INTERDIT                                  |

---

## SECTION 7 — SIGNAUX STOP

  STOP-01  alembic heads > 1 ligne
  STOP-02  MRD_CURRENT_STATE next_milestone ≠ mandat reçu
  STOP-03  Railway ↔ local divergent sans table diff postée
  STOP-04  alias_preservation_rate < 0.99 sans justification
  STOP-05  duplicate_identity > 0
  STOP-06  destructive_loss > 0
  STOP-07  taxonomie réintroduite avant fin MRD-4
  STOP-08  agent modifie fichier hors périmètre
  STOP-09  downgrade() échoue ou absent
  STOP-10  LLM hors liste fermée sans UNRESOLVED
  STOP-11  branche milestone futur sans audit CTO
  STOP-12  DATABASE_URL contient railway pendant migration locale
  STOP-13  trigger identité absent après migration dict_items
  STOP-14  CASCADE FK détectée couche_b après MRD-3
  STOP-15  alembic current DB ≠ alembic heads repo après upgrade
  STOP-16  test rouge non documenté dans MRD0_SENTENCE_CTO.md
  STOP-17  document gelé SHA256 modifié — FREEZE_HASHES.md diverge

---

## SECTION 8 — FORMAT POST STOP

  SIGNAL STOP — [STOP-NN]
  Milestone   : MRD-N
  Etape       : N
  Timestamp   : YYYY-MM-DD HH:MM UTC
  CAUSE       : [description factuelle]
  OUTPUT BRUT : [output exact non reformulé]
  ÉTAT        : branch / heads / current / dernière étape complète
  QUESTION    : [une seule question binaire si possible]
  EN ATTENTE DE GO. Aucune action prise.

---

## SECTION 9 — FORMAT CLÔTURE MILESTONE

  docs/audits/MRD{N}_RESULT.md
  Contient : milestone, date, commit, tag, alembic heads/current,
             invariants PASS/FAIL/N/A, triggers, cascade_fk,
             défaillances MRD-3 statut, outputs produits,
             tests résultat, métriques, statut DONE/NOT DONE.
  Règle : un FAIL non justifié = merge interdit.

---

## SECTION 10 — RÈGLE AGENT BLOC DE TÊTE

  ===================================================
  LECTURE OBLIGATOIRE AVANT TOUTE ACTION
  ===================================================
  0. docs/freeze/SYSTEM_CONTRACT.md
  1. docs/freeze/DMS_V4.1.0_FREEZE.md
  2. docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md
  3. docs/freeze/DMS_MRD_PLAN_V1.md
  4. docs/freeze/MRD_CURRENT_STATE.md
     -> Si next_milestone != ce mandat : STOP immédiat
  5. docs/freeze/BASELINE_MRD_PRE_REBUILD.md
  6. mandat du milestone en cours
  Puis : python scripts/validate_mrd_state.py
  Si exit(1) -> STOP. Poster. Attendre GO CTO.
  ===================================================

---

## SECTION 11 — PROTOCOLE REPRISE INTERRUPTION

  Session interrompue = incapacité à compléter l'étape courante.
  L'agent documente l'état exact et attend le CTO.
  CTO décide : ROLLBACK ou REPRISE-N.
  L'agent ne reprend jamais depuis le début seul.
  L'agent ne résout jamais un conflit de merge seul.

---

## SECTION 12 — PRINCIPE DIRECTEUR

  Nous ne colmatons plus M7.
  Nous repartons du dernier point sûr.
  Nous conservons le vrai. Nous figeons le suspect.
  Nous déprécions la fausse doctrine.
  Nous reconstruisons le registre depuis le réel.
  Nous réintroduisons l'identité sur base canonique.
  Nous redonnons à M7 son vrai rôle : enrichir, pas fonder.
  Chaque agent exécute. Le CTO décide.

---

## SECTION 13 — CHECKSUMS

  SHA256 : [GÉNÉRÉ À ÉTAPE 5 DU MANDAT MRD-0]
  Commande : sha256sum docs/freeze/DMS_MRD_PLAN_V1.md
  Amendement -> DMS_MRD_PLAN_V1.1_PATCH.md signé AO
  Ce fichier n'est plus modifié après hash.
