# AUDIT TECHNIQUE SENIOR — DMS V4.1 / PRÉ-M12
## Rapport d'évaluation brutale — Lecture sans filtre

```
Auditeur    : CTO Senior / DevOps (audit indépendant)
Date        : 2026-03-17
Périmètre   : Dépôt complet — lecture seule
Commit HEAD : 1cabcf3 (Merge PR #203 — feat/m11-ocr-files-api)
Statut MRD  : last_completed = M11 — next = M12
Verdict     : BUILD VIABLE ≠ ENTERPRISE-GRADE
```

---

## 0. PRÉAMBULE — MÉTHODE D'AUDIT

Ce rapport est produit en lecture seule. Aucun fichier n'a été modifié.
L'analyse couvre : structure repo · chaîne Alembic · CI/CD · sécurité ·
qualité code · dette technique · fichiers nuisibles · convergence vers
la vision M12 · enterprise readiness.

Chaque faille est classée **ASAP** (bloquante pré-M12) ou **DETTE**
(acceptable après M12, à planifier).

---

## 1. VERDICT GLOBAL

| Dimension                    | Note  | Verdict           |
|------------------------------|-------|-------------------|
| Architecture conceptuelle    | 8/10  | ✅ Solide          |
| Qualité des migrations       | 4/10  | ❌ Problèmes actifs|
| Sécurité applicative         | 6/10  | ⚠️ Risques ouverts |
| CI/CD                        | 6/10  | ⚠️ Gates trop lâches|
| Lisibilité / maintenabilité  | 4/10  | ❌ Pollution sévère|
| Couverture de tests          | 5/10  | ⚠️ Stubs bloquants |
| Enterprise-grade             | 3/10  | ❌ Pas encore      |
| Convergence vision M12       | 6/10  | ⚠️ Pré-requis manquants|

**Conclusion directe :** L'architecture conceptuelle est saine et bien
pensée. La séparation Couche A / Couche B est structurellement correcte.
Mais le dépôt souffre d'une pollution documentaire et opérationnelle
sévère qui nuit à sa lisibilité, à sa maintenabilité et à sa
enterprise-readiness. Il y a des violations architecturales actives et
des dettes non résolues qui BLOQUENT M12.

---

## 2. FICHIERS NUISIBLES ET ORPHELINS — POLLUTION DU DÉPÔT

### 2.1 Fichiers de logs/artefacts versionnés à la racine (CRITIQUE)

**37 fichiers .txt versionnés à la racine du dépôt** — tous sont des
artefacts de session de travail (sorties de scripts, résultats pytest,
logs de build) qui n'ont AUCUNE place dans git.

```
alembic_m74.txt, alembic_m74a.txt   — snapshots alembic (données de session)
audit_abc.txt                        — 34 KB de log d'audit brut
backfill_dry.txt, backfill_reel.txt  — logs de backfill (données prod leaked?)
build_err.txt (125 KB!), build_out.txt — logs de build complets
m11_e7_out.txt (3.7 MB!)             — FICHIER LE PLUS GRAVE : 3.7 MB de log
pytest_result.txt, pytest_result2.txt — sorties pytest
run_dict_*.txt (plusieurs)           — logs d'exécution de scripts dict
phase_a_*.txt                        — sorties de phase
probe_*.txt                          — outputs de probes
```

**Impact réel :**
- `m11_e7_out.txt` = 3.7 MB dans git → ralentit chaque `git clone`
- `build_err.txt` = 125 KB de stack traces potentiellement sensibles
- Signale une discipline de travail non adaptée à un dépôt partagé
- Masque les fichiers importants dans `git status`
- Ces fichiers ne sont PAS dans `.gitignore` — **omission grave**

**1 fichier CSV versionné :**
```
mercurials_mapping_proposals.csv (302 KB) — données marché potentiellement sensibles
```

**4 fichiers .txt dans scripts/ :**
```
scripts/_dryrun_wave2_output.txt
scripts/_err_wave2.txt
scripts/_out_wave2.txt
scripts/_wave2_dryrun.txt
```

**Verdict ASAP :** Ces 42+ fichiers doivent être retirés du versionnement
et ajoutés au `.gitignore`. Ils rendent la navigation du dépôt difficile
et signalent un manque de discipline git fondamental.

### 2.2 Scripts `_probe_*` dans scripts/ (38 fichiers)

38 scripts préfixés `_probe_*.py` dans `scripts/` sont des outils de
diagnostic ad-hoc de sessions passées. Ils ont un rôle temporaire
(vérifier l'état d'un milestone) et aucun rôle permanent.

**Problème :** Ils n'ont pas d'index, pas de documentation commune, et
plusieurs pointent vers Railway directement. Sans contexte, un développeur
entrant ne peut pas distinguer les scripts "officiels" des probes
jetables.

**Verdict DETTE :** Créer un `scripts/README.md` avec l'inventaire des
scripts officiels vs sondes temporaires. Les sondes archivées à supprimer
progressivement.

### 2.3 ADR éparpillés dans 3 répertoires différents

```
docs/adr/          — 20+ ADRs (format MRD)
docs/adrs/         — 16+ ADRs (format V3.3.2)
docs/ADR-0006.md   — 2 ADRs à la racine de docs/
```

**Impact :** Un développeur ne sait pas où chercher un ADR. La navigation
est impossible sans grep. `docs/ADR-0006.md` et `docs/ADR-0008.md`
existent à la racine de `docs/` ET dans `docs/adrs/`.

**Verdict DETTE :** Unifier sous `docs/adrs/` avec un index `INDEX.md`.
Les doublons à déduire/archiver.

### 2.4 Documentation dupliquée et éparpillée

```
docs/audit/    — 3 fichiers
docs/audits/   — 50+ fichiers (dont le présent rapport)
docs/archives/ — sous-dossier defaillances
```

50+ rapports d'audit accumulés depuis février 2026 sans archivage ni
indexation. `AUDIT_M4_M7_*` : 7 fichiers sur le même sujet.
`CI_*.md` : 8 fichiers sur les corrections CI.

**Verdict DETTE :** Créer `docs/audits/INDEX.md` et archiver les rapports
résolus dans `docs/archives/audits/`.

### 2.5 Fichiers Markdown à la racine (surcharge cognitive)

La racine contient **15 fichiers Markdown** dont plusieurs
redondants ou de portée très étroite :

```
CREER_DB.md, CREER_DB_DBEAVER.md   — même sujet, deux fichiers
OU_TROUVER_PGADMIN.md              — guide d'outil local, sans valeur durable
RESET_PASSWORD.md                  — procédure ponctuelle
TROUBLESHOOTING_DB.md              — non maintenu
IMPLEMENTATION_SUMMARY.md          — 13 KB de résumé devenu obsolète
```

**Verdict DETTE :** Consolider dans `docs/RUNBOOK.md` (qui existe déjà)
et retirer les doublons.

---

## 3. ANALYSE DE LA CHAÎNE ALEMBIC — FAILLES CRITIQUES

### 3.1 Doublons de numéros de révision (CRITIQUE)

Quatre groupes de fichiers partagent le même préfixe numérique :

| Préfixe | Fichiers | Commentaire |
|---------|----------|-------------|
| `009`   | `009_add_supplier_scoring_tables.py` + `009_supplier_scores_eliminations.py` | Branches parallèles résolues par `010` |
| `040`   | `040_geo_master_mali.py` + `040_mercuriale_ingest.py` | Branches parallèles non numérotées différemment |
| `042`   | `042_market_surveys.py` + `042_vendor_fixes.py` | Idem |
| `043`   | `043_market_signals_v11.py` + `043_vendor_activity_badge.py` | Idem |

**Verdict :** Ces fichiers ont des `revision` IDs distincts et des
`down_revision` différents — ils forment des branches parallèles qui
convergent via des merge migrations. La chaîne est techniquement
valide (1 seul HEAD = `048_vendors_sensitive_data`).

**MAIS** : les nommages identiques induisent en erreur tout lecteur.
Un `ls alembic/versions/` montre des doublons apparents. Cela viole
INV-09 du plan MRD ("1 migration = 1 branche = 1 merge = 1 tag") dans
l'esprit.

**Verdict DETTE :** Les prochaines migrations doivent utiliser des préfixes
uniques ou le format `mXX_` pour éviter toute ambiguïté visuelle.

### 3.2 Divergence grave MRD_CURRENT_STATE vs réalité repo (CRITIQUE)

`docs/freeze/MRD_CURRENT_STATE.md` déclare :
```
local_alembic_head : 045_agent_native_foundation
```

La réalité du dépôt :
```
HEAD réel : 048_vendors_sensitive_data
```

**Écart : 3 migrations non documentées** —
`046_imc_category_item_map`, `046b_imc_map_fix_restrict_indexes`,
`047_couche_a_service_columns`, `048_vendors_sensitive_data`.

Le SYSTEM_CONTRACT stipule que `MRD_CURRENT_STATE.md` est la "source
de vérité unique" mise à jour après chaque merge. Ce n'est pas le cas.
La source de vérité **ment activement**.

**Verdict ASAP :** `MRD_CURRENT_STATE.md` doit être mis à jour avant M12.

### 3.3 Migration 018 vide (migration fantôme)

`018_fix_alembic_heads.py` est décrit dans les commentaires comme une
"migration vide avec down_revision" dont le seul rôle était de fixer la
chaîne. Ce type de migration fantôme est une dette de lisibilité et
d'opérabilité.

**Verdict DETTE :** Acceptable dans le passé, à ne pas reproduire.

### 3.4 migration 017 absente

La séquence passe de 016 à 018 directement. Il n'existe pas de fichier
`017_*.py`. Cela est explicitement documenté dans
`019_consolidate_extraction_corrections.py` comme correction de la
migration 018 qui était elle-même un correctif. Ce triple saut de
versions (016→018→019) est une marque de dettes accumulées.

**Verdict DETTE :** Documenté, mais signale une phase d'instabilité
passée sur le schéma d'extraction.

### 3.5 Divergence Railway vs local (BLOQUANT pour M12)

`MRD_CURRENT_STATE.md` documente une divergence Railway vs local :
```
Railway : 044_decision_history
Local   : 048_vendors_sensitive_data (réalité repo)
```

**4 migrations** non appliquées sur Railway. Toute activation de
fonctionnalité basée sur les migrations 045-048 sera silencieusement
cassée en production.

**Verdict ASAP :** Les migrations 045 à 048 doivent être appliquées sur
Railway avant tout déploiement lié à M12.

---

## 4. VIOLATIONS ARCHITECTURALES ACTIVES

### 4.1 `from sqlalchemy import text` dans `src/` (VIOLATION CONSTITUTION)

La Constitution V3.3.2 §3 interdit l'ORM. REGLE-41 des ADR migrations
interdit `import sqlalchemy` dans les migrations. Or :

```
src/couche_a/scoring/engine.py   — from sqlalchemy import text (L13)
src/api/auth_helpers.py          — from sqlalchemy import text (L20)
```

L'utilisation de `sqlalchemy.text()` comme wrapper de requête SQL brute
est une zone grise — ce n'est pas un ORM à proprement parler. Cependant :
1. Cela crée une dépendance SQLAlchemy dans `src/` qui n'est pas dans
   `requirements.txt` directement (héritage via alembic).
2. Cela crée un couplage fragile : si alembic change sa version de SQLAlchemy,
   le code applicatif peut casser silencieusement.
3. Cela viole l'esprit de "requêtes paramétrées via psycopg exclusivement".

**Verdict ASAP :** Remplacer par `psycopg` natif, cohérent avec le reste
de `src/`.

### 4.2 `from sqlalchemy import text` dans les migrations pre-m4 (VIOLATION REGLE-41)

```
alembic/versions/002 à 011 — 10 migrations avec from sqlalchemy import text
```

REGLE-41 : "import sqlalchemy est interdit dans les migrations ; utiliser
op.execute() avec SQL brut uniquement". Ces migrations antérieures violent
la règle mais sont **gelées** (Alembic immutable). C'est une dette
historique irrémédiable.

**Verdict DETTE PERMANENTE :** Les migrations existantes ne peuvent pas
être modifiées (REGLE-ANCHOR-05). À documenter comme exception historique
dans un addendum à REGLE-41.

### 4.3 Rate limiting per-route désactivé silencieusement (SÉCURITÉ)

Dans `src/ratelimit.py` :
```python
def conditional_limit(rate_limit: str):
    """Désactivé pour éviter les problèmes de wrapping."""
    def decorator(func):
        return func  # ← NO-OP TOTAL
    return decorator
```

Avec le commentaire `TODO : réactiver les limites par-route après audit
slowapi/FastAPI compat`.

**Impact :** Seule la limite globale de 100/minute par IP est active.
Les routes critiques (auth, upload, scoring) n'ont aucune limite
individuelle. Un attaquant peut hammerer `/api/auth/token` à 100 req/min
sans déclenchement de protection spécifique.

**Verdict ASAP :** La solution de contournement est acceptable en
développement. Elle est inacceptable en production pré-M12. L'audit de
compatibilité slowapi/FastAPI doit être résolu.

### 4.4 Rate limiter en mémoire `storage_uri="memory://"` (SÉCURITÉ/SCALABILITÉ)

```python
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",  # ← Utiliser Redis en production
)
```

**Impact :** Sur Railway avec plusieurs workers ou un redémarrage, les
compteurs de rate limit sont perdus. Un attaquant peut contourner le
rate limiting en attendant un restart ou en exploitant du multi-worker.

**Verdict ASAP :** Redis est dans `requirements.txt` (redis==5.2.1).
L'intégration doit être activée avant M12. Un fallback `memory://`
conditionnel sur `TESTING=true` est acceptable.

### 4.5 JWT — `python-jose` avec dépendance `cryptography>=42.0.0` (VIGILANCE)

`python-jose[cryptography]==3.3.0` est utilisé pour JWT. `python-jose`
n'est plus activement maintenu (dernier release : 2022). Il dépend de
`cryptography>=42.0.0` (conforme) mais la bibliothèque elle-même a des
vulnérabilités non corrigées documentées.

La logique JWT est bien conçue (jti, blacklist, rotation), mais la
bibliothèque sous-jacente est un risque.

**Verdict DETTE :** Planifier migration vers `PyJWT` (activement maintenu)
post-M12.

### 4.6 f-strings dans constructions SQL partielles (VIGILANCE)

```python
# src/couche_a/committee/service.py:46
f"SELECT * FROM public.committees WHERE committee_id = %s {lock_clause}"

# src/vendors/repository.py:172, 185
f"SELECT {_PUBLIC_COLUMNS_SQL} FROM vendors WHERE vendor_id = %(vid)s"

# src/geo/repository.py:16, 94
f"SELECT * FROM geo_countries {where} ORDER BY name_fr"
```

Dans les cas ci-dessus, `lock_clause`, `_PUBLIC_COLUMNS_SQL` et `where`
sont des **constantes ou variables contrôlées en interne** — pas d'input
utilisateur direct. La Constitution est respectée pour les paramètres
utilisateur (usage de `%s`/`%(name)s`).

**MAIS** `where` dans `geo/repository.py` mérite une inspection : si
jamais un paramètre utilisateur transite par cette variable, l'injection
est possible.

**Verdict ASAP (vérification) :** Auditer `where` dans `geo/repository.py`
pour s'assurer qu'il n'est jamais construit à partir d'input utilisateur.

### 4.7 `SELECT *` dans des requêtes de production (ANTI-PATTERN)

```python
# src/couche_a/committee/service.py:46
f"SELECT * FROM public.committees WHERE committee_id = %s..."

# src/geo/repository.py:16, 94
f"SELECT * FROM geo_countries {where}..."
```

`SELECT *` est un anti-pattern en production : il retourne tous les
champs y compris les futurs champs sensibles ajoutés par une migration,
expose plus de données que nécessaire, et est plus lent.

**Verdict DETTE :** Remplacer par des listes de colonnes explicites.

---

## 5. CI/CD — ANALYSE DES WORKFLOWS

### 5.1 Gates milestones référençant des IDs obsolètes (INCOHÉRENCE)

`ci-milestones-gates.yml` vérifie l'ordre des milestones :
```yaml
ORDER=("M0-BOOT" "M1-DATABASE" "M2-UPLOAD" "M3A-EXTRACTION"
       "M3B-SCORING" "M4-TESTS" "M5-TEMPLATES" "M6-GENERATION"
       "M7-OCR" "M8-MARKET" "M9-SECURITY" "M10-UX" "M-CI-INVARIANTS")
```

Ces IDs (`M0-BOOT`, `M1-DATABASE`, etc.) **ne correspondent à aucun
fichier `.done` dans `.milestones/`**. Les fichiers `.done` réels sont :
```
M-ANALYSIS-SUMMARY.done, M-COMMITTEE-CORE.done, M-CRITERIA-FK.done...
M-SCORING-ENGINE.done, M-PIPELINE-A-E2E.done...
```

Les deux nomenclatures sont entièrement différentes. Le workflow
`ci-milestones-gates.yml` est **effectivement mort** — il ne bloque
jamais rien car aucun de ses fichiers cibles n'existe.

**Verdict ASAP :** Le gate est un zombie. Soit le synchroniser avec les
vraies nomenclatures de `.milestones/`, soit le désactiver explicitement.

### 5.2 Gate coverage : `fail_under=0` par défaut (DANGEREUX)

```yaml
if [ -f .milestones/M-TESTS.done ]; then
    echo "fail_under=40"
else
    echo "fail_under=0"
```

`.milestones/M-TESTS.done` **n'existe pas** → `fail_under=0` permanent.
161 fichiers de test existent mais la CI accepte 0% de couverture.

**Verdict ASAP :** `M-TESTS.done` doit être créé ou la valeur par défaut
doit être augmentée. Un projet avec 161 tests qui tolère 0% de couverture
est en contradiction avec lui-même.

### 5.3 `ci-freeze-integrity.yml` vérifie un répertoire qui EXISTE

```yaml
test -f docs/freeze/v3.3.2/SHA256SUMS.txt || exit 1
test -f docs/freeze/v3.3.2/FREEZE_MANIFEST.md || exit 1
sha256sum -c docs/freeze/v3.3.2/SHA256SUMS.txt
```

`docs/freeze/v3.3.2/` existe et contient les fichiers requis. Ce gate
est **fonctionnel**. ✅

### 5.4 Invariants CI gate optionnel (FAIBLESSE)

`ci-invariants.yml` ne bloque que si `.milestones/M-CI-INVARIANTS.done`
existe. Ce fichier n'existe pas → les tests d'invariants ne bloquent pas
la CI malgré 161 fichiers de tests dont beaucoup testent précisément
les invariants constitutionnels.

**Verdict DETTE :** Le mécanisme de gates progressifs est une bonne
pratique en phase de construction. Mais à l'approche de M12, les gates
critiques doivent être activés.

### 5.5 Postgres 15 en CI, Postgres 16 en développement local

```yaml
# CI : postgres:15
# docker-compose.yml : postgres:16
```

Version mismatch entre CI et local. Risque de comportements différents
sur les triggers PL/pgSQL et les index. À minima, à documenter.

**Verdict DETTE :** Aligner sur une version. Préférer la version prod
(Railway impose Postgres 15 ou 16 — à confirmer).

---

## 6. DETTE TECHNIQUE ACTIVE NON RÉSOLUE

### 6.1 FK `pipeline_runs.case_id` NOT VALID (CRITIQUE INTÉGRITÉ)

Documenté dans `TECHNICAL_DEBT.md` :
```
fk_pipeline_runs_case_id : NOT VALID
Cause : Lignes orphelines détectées au PROBE-SQL-01 M0B
```

Une contrainte FK `NOT VALID` signifie que **les données existantes ne
respectent pas la contrainte**. Des `pipeline_runs` pointent vers des
`cases` qui n'existent pas. Cela compromet l'intégrité référentielle
et peut provoquer des comportements inattendus dans les requêtes jointes.

**Verdict ASAP :** Auditer et supprimer les orphelins, puis
`ALTER TABLE pipeline_runs VALIDATE CONSTRAINT fk_pipeline_runs_case_id`.

### 6.2 `time.sleep(2)` stub dans `extract_offer_content` (FONCTIONNEL CASSÉ)

```python
# src/couche_a/extraction.py:416
time.sleep(2)
return {"status": "completed"}
```

L'extraction documentaire est le **cœur fonctionnel de la Couche A**.
La fonction principale retourne un dictionnaire statique après un sleep.
Toute l'infrastructure d'extraction (pipeline, scoring, exports) repose
sur cette fonction qui est un mock.

M11 a livré l'OCR via Mistral (`services/annotation-backend/`), mais ce
service est **découplé** du pipeline principal FastAPI. Le pont entre
l'annotation-backend et `extract_offer_content` dans le main pipeline
n'existe pas.

**Verdict ASAP pour M12 :** Sans extraction réelle, M12 (Procedure
Recognizer avec precision ≥ 0.70) est **architecturalement impossible**
à valider.

### 6.3 Colonnes PK non conformes au freeze

Documenté dans `TECHNICAL_DEBT.md` :
```
procurement_references.id : TEXT (attendu UUID)
documents.id              : TEXT (attendu UUID)
committee_members.PK      : member_id (attendu: id)
```

**Verdict DETTE :** Post-beta. Mais le mélange `TEXT`/`UUID` dans les PKs
est un risque à mesure que les jointures se multiplient.

### 6.4 `documents.sha256` nullable sans backfill (INTÉGRITÉ)

```
documents.sha256 : nullable — ajouté par 036_db_hardening
Backfill requis : UPDATE documents SET sha256 = ... WHERE sha256 IS NULL
NOT NULL à poser après backfill
```

La colonne `sha256` est censée garantir l'intégrité des documents. Si
elle est nullable, la garantie est creuse.

**Verdict ASAP :** Le backfill est trivial. Le NOT NULL doit être posé
avant M12.

### 6.5 `src/couche_a/llm_router.py` absent malgré référence dans TECHNICAL_DEBT

`TECHNICAL_DEBT.md` documente :
```
LLM router (llm_router.py) : Absent — Module non créé — défini dans
freeze V4.1.0, M10A
```

Le fichier `src/couche_a/llm_router.py` n'existe pas à la racine
`src/couche_a/`. Il existe un fichier du même nom dans le module couche_a
mais sans le contenu attendu du routeur LLM.

**Verdict ASAP :** Ce module est une pré-condition à M12 (Procedure
Recognizer via LLM).

### 6.6 Stubs `ExtractionField` / `TDRExtractionResult` absents

Documenté dans `TECHNICAL_DEBT.md` : modèles définis dans le freeze
V4.1.0, non implémentés. M12 (Procedure Recognizer) dépend directement
de ces structures.

**Verdict ASAP :** Bloqueront M12.

---

## 7. PRÉ-REQUIS M12 NON SATISFAITS

M12 est défini comme "PROCEDURE RECOGNIZER" avec les conditions :
- ≥ 15 `annotated_validated` avant M12 (RÈGLE-23)
- Precision recall ≥ 0.70 sur critères
- Corpus annoté présent dans `annotation_registry`

**Inventaire des blocages M12 :**

| Prérequis | Statut | Criticité |
|-----------|--------|-----------|
| ≥ 15 annotated_validated dans DB | Non vérifiable sans DB | BLOQUANT |
| Precision ≥ 0.70 sur critères | Non mesurable (stub) | BLOQUANT |
| `llm_router.py` implémenté | ABSENT | BLOQUANT |
| `ExtractionField`/`TDRExtractionResult` | ABSENTS | BLOQUANT |
| `extract_offer_content` opérationnel | STUB (time.sleep) | BLOQUANT |
| Railway synchronisé avec repo (045→048) | NON | BLOQUANT |
| FK `pipeline_runs.case_id` VALIDATED | NON | BLOQUANT |
| `MRD_CURRENT_STATE.md` à jour | NON (écart 3 migrations) | BLOQUANT |
| Rate limit per-route actif | NON (conditional_limit no-op) | MAJEUR |
| Redis en production | NON (memory://) | MAJEUR |
| `M-TESTS.done` créé (coverage gate actif) | NON | MAJEUR |

**Verdict direct : M12 NE PEUT PAS DÉMARRER dans l'état actuel.**
Au minimum 7 blocages doivent être levés.

---

## 8. ÉVALUATION ENTERPRISE-GRADE

### Ce qui est enterprise-grade ✅

- **Architecture conceptuelle** : Couche A / Couche B avec séparation
  stricte, détection via tests AST (`test_couche_a_b_boundary.py`).
  C'est une bonne pratique qui n'existe pas dans la plupart des projets
  de cette taille.

- **Append-only + audit trail** : Triggers DB sur les tables critiques,
  hash chain pour l'audit (`038_audit_hash_chain.py`). Indispensable pour
  procurement public.

- **Doctrine d'échec explicite** : Les exports incomplets sont marqués
  comme tels, jamais silencieux. Conforme aux exigences d'audit.

- **RBAC avec 5 rôles** : Bien défini (ADR-M1-002), implémenté avec
  vérification des claims JWT.

- **Token blacklist + rotation** : Pattern JWT correct avec `jti` et
  révocation en DB. Rare et bienvenu.

- **SYSTEM_CONTRACT + CONTEXT_ANCHOR** : Gouvernance documentaire
  structurée. Les LLM agents sont contraints par un contrat écrit.
  Approche innovante pour un projet à forte utilisation IA.

- **Migration Alembic séquentielle** : 1 seul HEAD, migration freeze
  V3.3.2 intacte, processus de downgrade documenté.

- **Magic bytes validation** (`filetype`, `werkzeug.secure_filename`) :
  La sécurité upload est correctement implémentée.

### Ce qui N'EST PAS enterprise-grade ❌

- **Pas de multi-tenancy** : L'architecture cible
  (`DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.md`) est conçue pour être
  tenant-ready, mais le schéma actuel n'a aucune colonne `tenant_id`.
  Un refactoring de migration serait catastrophique sans planification.

- **Pas de secrets management** : Pas de Vault, pas de rotation
  automatique des secrets. `SECRET_KEY` est passée par variable
  d'environnement sans procédure de rotation documentée.

- **Monitoring/observabilité absent** : Pas de Prometheus, pas de
  tracing (OpenTelemetry), pas d'alerting. `AgentRunContext` est un bon
  début pour le FinOps LLM mais ne couvre pas l'application générale.

- **Pas de HTTPS enforcement applicatif** : FastAPI ne force pas HTTPS
  (délégué à Railway/Nginx). Acceptable pour SaaS mais à documenter.

- **Coverage à 0% par défaut** : Inacceptable pour enterprise. Les 161
  tests constituent un réseau de sécurité solide sur le papier, mais le
  gate n'est pas activé.

- **Pas de stratégie de disaster recovery documentée** : `DEPLOYMENT.md`
  (1.1 KB) est insuffisant pour un système de procurement public.

- **Artefacts de développement en production** : Les 37 fichiers .txt
  versionnés dans un repo enterprise déclassifieraient immédiatement un
  audit SOC2.

---

## 9. ÉVALUATION DE LA CONVERGENCE VERS LA VISION

La vision DMS est clairement articulée :
> Réduire 90% du travail cognitif répétitif en procurement public.

**Où le build converge vers la vision :**

- Pipeline Couche A (extraction → normalisation → scoring → exports) :
  architecture complète, modules présents, tests nombreux.
- Comité avec LOCK irréversible et snapshot décisionnel : implémenté.
- Dictionnaire canonique Sahel avec fingerprint/item_code : implémenté
  (MRD-4 à MRD-6).
- Signaux marché et formule V1.1 : implémentés (M8/M9/M11).
- Vendor identity avec pseudonymisation : implémenté.
- Annotation backend Mistral : livré (M11).

**Où le build diverge de la vision :**

- **Extraction documentaire** : Le module central est un stub
  `time.sleep(2)`. La vision ne peut pas être validée sans extraction
  réelle. L'annotation-backend existe mais n'est pas connecté au
  pipeline principal.
- **SLA 60 secondes** : 3 tests skipped sur le SLA (60s Classe A,
  queue Classe B). La promesse fondamentale du système n'est pas testée.
- **Interface utilisateur** : Hors scope direct, mais aucun frontend
  documenté. Le DMS est une API sans UI propre aujourd'hui.
- **Annotation corpus** : 0 documents `annotated_validated` vérifiables
  dans le repo. M12 exige 15 minimum.

---

## 10. PLAN DE CORRECTION — CLASSIFICATION

### ASAP (Avant de démarrer M12 — Maximum 5 jours)

| ID | Action | Fichier(s) cibles | Impact |
|----|--------|-------------------|--------|
| ASAP-01 | Retirer les 37+ fichiers .txt et 1 .csv de git, les ajouter au `.gitignore` | `.gitignore` | Pollution git éliminée |
| ASAP-02 | Mettre à jour `MRD_CURRENT_STATE.md` : `local_alembic_head = 048_vendors_sensitive_data` + Railway pendantes | `docs/freeze/MRD_CURRENT_STATE.md` | Source de vérité alignée |
| ASAP-03 | Appliquer migrations 045→048 sur Railway (avec GO CTO explicite) | Railway (hors repo) | Alignement prod/local |
| ASAP-04 | Créer `.milestones/M-TESTS.done` pour activer le gate coverage à 40% | `.milestones/M-TESTS.done` | CI gate actif |
| ASAP-05 | Auditer et purger orphelins `pipeline_runs.case_id`, puis VALIDATE CONSTRAINT | Migration dédiée | Intégrité FK rétablie |
| ASAP-06 | Backfill `documents.sha256` puis `ALTER COLUMN SET NOT NULL` | Migration dédiée | Intégrité SHA256 |
| ASAP-07 | Activer Redis pour rate limiting (remplacer `memory://` par `REDIS_URL`) | `src/ratelimit.py` | Sécurité production |
| ASAP-08 | Résoudre `conditional_limit` no-op : auditer compatibilité slowapi/FastAPI, réactiver les limites per-route | `src/ratelimit.py` | Sécurité per-route |
| ASAP-09 | Remplacer `from sqlalchemy import text` par psycopg natif dans `src/` | `src/couche_a/scoring/engine.py`, `src/api/auth_helpers.py` | Conformité Constitution |
| ASAP-10 | Corriger `ci-milestones-gates.yml` : aligner les IDs sur les fichiers `.done` réels | `.github/workflows/ci-milestones-gates.yml` | Gate vivant |
| ASAP-11 | Implémenter `llm_router.py` et modèles `ExtractionField`/`TDRExtractionResult` | `src/couche_a/llm_router.py` | Prérequis M12 |
| ASAP-12 | Connecter `annotation-backend` au pipeline principal (pont `extract_offer_content`) | `src/couche_a/extraction.py` | Vision M12 réalisable |

### DETTE TECHNIQUE (Planifier post-M12)

| ID | Action | Effort | Priorité |
|----|--------|--------|----------|
| DETTE-01 | Unifier `docs/adr/` et `docs/adrs/` en un seul répertoire + `INDEX.md` | 2h | Haute |
| DETTE-02 | Archiver les 50+ rapports d'audit anciens dans `docs/archives/audits/` | 1h | Haute |
| DETTE-03 | Créer `scripts/README.md` avec inventaire officiel vs sondes | 3h | Haute |
| DETTE-04 | Consolider les 15 Markdown racine dans `docs/RUNBOOK.md` | 4h | Moyenne |
| DETTE-05 | Remplacer `SELECT *` par sélections explicites dans repository.py | 4h | Haute |
| DETTE-06 | Migrer `python-jose` vers `PyJWT` (maintenance active) | 1j | Haute |
| DETTE-07 | Documenter exception historique REGLE-41 pour migrations 002-011 | 1h | Basse |
| DETTE-08 | Aligner version Postgres CI (15) et local (16) | 1h | Moyenne |
| DETTE-09 | Normaliser les PKs TEXT → UUID sur `procurement_references`, `documents` | 1j migration | Haute |
| DETTE-10 | Ajouter stratégie DR (Disaster Recovery) dans `docs/RUNBOOK.md` | 4h | Haute |
| DETTE-11 | Activer `M-CI-INVARIANTS.done` pour rendre les tests d'invariants bloquants | 30min | Haute |
| DETTE-12 | Plan multi-tenancy : ajouter `tenant_id` sur les tables core (Architecture Section 3) | 3j migration | Critique post-M15 |
| DETTE-13 | Monitoring/observabilité : intégrer OpenTelemetry ou équivalent | 3j | Haute |

---

## 11. CONCLUSION — MESSAGE DIRECT AU CTO

**Ce que vous avez bien fait :**

La séparation Couche A / Couche B avec tests AST bloquants est une
décision architecturale excellente. Le SYSTEM_CONTRACT comme couche zéro
de gouvernance agent est innovant et bien exécuté. L'append-only avec
hash chain pour l'audit procurement est exactement ce qu'il faut pour
un système destiné aux appels d'offres publics. La vision produit est
limpide.

**Ce qui est urgent :**

Le dépôt a accumulé 37 fichiers de logs versionnés (dont un de 3.7 MB),
la source de vérité documentaire (MRD_CURRENT_STATE) ment sur la tête
Alembic, et l'extraction documentaire — cœur de la promesse produit —
est un stub `time.sleep(2)`. Ces trois éléments, combinés, signifient
que M12 n'est pas un problème de milestone mais un problème de fondation.

**Ce qui doit se passer avant M12 :**

Les 12 points ASAP de la section 10 représentent environ 4-5 jours de
travail propre. Sans les ASAP-01 à ASAP-12, M12 est une promesse
impossible à tenir.

**Enterprise-grade : pas encore.**

Le système a les bases. Il n'a pas la discipline opérationnelle. La
différence entre un bon projet solo et un système enterprise-grade, c'est
la rigueur dans les détails : git propre, gates actifs, sources de vérité
synchronisées, sécurité production-ready. Ces éléments sont corrigibles
en quelques jours. Ils doivent l'être maintenant.

---

*Rapport produit en lecture seule — aucun fichier modifié.*
*Audit exhaustif sur commit HEAD `1cabcf3` — date 2026-03-17.*
