# DMS ORCHESTRATION FRAMEWORK V1 — VERSION FINALE

## Statut : PRÊT POUR FREEZE
## Date : 2026-03-08
## Décideur : AO — Abdoulaye Ousmane
## Amendable : uniquement par ADR signé AO

---

## HIÉRARCHIE DE LECTURE OBLIGATOIRE

Tout agent lit dans cet ordre exact, sans exception, sans raccourci :

```
1. docs/freeze/DMS_V4.1.0_FREEZE.md              ← loi produit
2. docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md  ← loi d'exécution (présent)
3. docs/freeze/DMS_MRD_PLAN_V1.md                ← plan de redressement
4. docs/freeze/BASELINE_MRD_PRE_REBUILD.md        ← état mesuré du terrain
5. mandat du milestone courant                    ← périmètre local
```

**Règle absolue :**
- Un agent ne peut pas lire l'état (4) avant la loi (2)
- Un agent ne peut pas lire le mandat (5) avant le plan (3)
- Tout conflit entre couches → résolu par la définition ci-dessous
- Tout cas non résolu → STOP, poster au CTO

**Définition de conflit inter-couches :**

```
CONFLIT   : couche N dit explicitement X, couche N+1 dit NOT-X
            → couche supérieure (N) gagne, toujours, sans exception

SILENCE   : couche N ne traite pas le cas, couche N+1 le traite
            → couche N+1 s'applique, pas de conflit, pas de STOP

AMBIGUÏTÉ : couche N est interprétable dans deux sens ou plus
            → STOP immédiat. Poster au CTO. L'agent ne tranche jamais.
```

---

## PARTIE 1 — SOURCE DE VÉRITÉ UNIQUE

```
PostgreSQL Railway = seule vérité sur l'état des données
git origin/main    = seule vérité sur le code validé
alembic heads      = doit être exactement 1 ligne après chaque merge
```

Toute divergence entre ces 3 sources = signal STOP immédiat.
L'agent ne résout pas la divergence. Il la poste et attend le CTO.

---

## PARTIE 2 — INVARIANTS SYSTÈME

Les invariants sont classés en deux catégories :

- **VRAIS MAINTENANT** : vérifiables et vrais en prod Railway aujourd'hui
- **CIBLE** : obligatoires, pas encore vrais, à atteindre par milestone spécifié

### Invariants VRAIS MAINTENANT

```
INV-01  item existe indépendamment de toute taxonomie

INV-02  identité item = indépendante de l'ordre SQL, du batch, du LLM,
        de toute taxonomie mutable.
        Un item ne change pas d'id quand sa catégorie change.

INV-03  rebuild registre = UPSERT fingerprint — jamais DELETE+INSERT

INV-04  append-only sur tables explicitement classées append-only
        (voir Partie 5 — liste fermée)

INV-05  hash chain préservée partout où posée — jamais mutation silencieuse

INV-06  LLM ne décide jamais seul — liste fermée obligatoire en Phase A et B
        Définition liste fermée : tout champ dont la valeur doit appartenir
        à un ensemble fini et prédéfini (catégorie, statut, type procédure,
        etc.) est soumis à une liste fermée. Le LLM propose. Le système
        valide contre la liste. Valeur hors liste → UNRESOLVED, jamais
        acceptée silencieusement.
        Phase A : milestones MRD-1 à MRD-5 (avant corpus annoté complet)
        Phase B : milestones MRD-6+ (corpus validé, seuils RÈGLE-23 atteints)
        En Phase B la liste fermée reste obligatoire. Le LLM peut avoir
        un seuil de confiance plus élevé mais ne décide jamais sans
        validation contre liste.

INV-07  taxonomie = conséquence de l'analyse du registre, jamais son socle.
        La taxonomie peut évoluer. L'identité des items ne suit pas.
        Complément de INV-02, non redondant : INV-02 protège l'identité,
        INV-07 protège l'ordre de construction.

INV-08  family_id legacy = read-only — triggers bloquants actifs en prod

INV-10  1 migration = 1 downgrade() réel et testé

INV-11  alembic heads = 1 ligne exactement après chaque merge

INV-12  Railway ↔ local : différentiel posté avant tout rebuild

INV-13  51 seeds human_validated = intouchables
        Vérification : COUNT human_validated = TRUE AND active = TRUE ≥ 51
        Valeur < 51 → STOP immédiat, poster au CTO
```

### Invariant CIBLE — obligatoire à partir de MRD-3

```
INV-09 — CIBLE MRD-3

  Baseline mesurée MRD-0 :
    CASCADE présente sur :
    couche_b.procurement_dict_aliases.item_id → procurement_dict_items.id

  Comportement attendu AVANT MRD-3 :
    La CASCADE DOIT RESTER PRÉSENTE telle que mesurée en baseline.
    Sa disparition non planifiée avant MRD-3 = régression → STOP immédiat.
    Sa présence = anomalie connue → noter dans clôture, ne pas bloquer.

  Comportement attendu APRÈS MRD-3 :
    Aucune CASCADE sur tables mémoire terrain.
    Toute détection après MRD-3 → STOP immédiat, régression critique.

  Règle de vérification :
    Avant MRD-3 : CASCADE présente → OK | CASCADE absente → STOP
    Après MRD-3 : CASCADE absente → OK | CASCADE présente → STOP
```

### Règle de vérification des invariants

```
Invariant VRAI MAINTENANT violé  → STOP immédiat, poster au CTO
INV-09 avant MRD-3 CASCADE présente → OK (anomalie connue, noter)
INV-09 avant MRD-3 CASCADE absente  → STOP (régression non planifiée)
INV-09 après MRD-3 CASCADE présente → STOP (régression critique)
INV-09 après MRD-3 CASCADE absente  → OK
```

---

## PARTIE 3 — PROTOCOLE SESSION OBLIGATOIRE

Tout agent, toute session, exécute ce bloc dans l'ordre exact avant toute action.

### S0 — Vérification variables d'environnement

```bash
python -c "
import os
required = ['DATABASE_URL', 'REDIS_URL', 'ENV']
missing = [v for v in required if not os.environ.get(v)]
if missing:
    print('VARIABLES MANQUANTES:', missing)
    print('STOP — ne pas continuer sans variables complètes')
    exit(1)
env = os.environ.get('ENV', 'unknown')
if env == 'production':
    print('ATTENTION : DATABASE_URL pointe sur PRODUCTION')
    print('Toute migration production = validation CTO explicite obligatoire')
    print('Ne pas continuer sans GO CTO documenté dans le mandat')
else:
    print(f'ENV={env} — OK pour opérations normales')
"
```

**Règle environnement :**
```
Toute migration en ENV=production = validation CTO explicite obligatoire.
Un agent ne migre jamais production sans GO CTO dans le mandat.
```

### S1 — Lecture des fichiers de vérité

```bash
cat docs/freeze/DMS_V4.1.0_FREEZE.md
cat docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md
cat docs/freeze/DMS_MRD_PLAN_V1.md
cat docs/freeze/BASELINE_MRD_PRE_REBUILD.md
```

### S2 — Probe état réel

```bash
# Git état
git branch --show-current
git log --oneline -3
git diff origin/main --name-only

# Stash — piège connu (voir Partie 8)
stash_count=$(git stash list | wc -l)
if [ "$stash_count" -gt "0" ]; then
    echo "ALERTE : $stash_count entrées stash présentes"
    git stash list
    echo "Vérifier avec CTO si stash contient WIP non committé"
fi

# Alembic
alembic heads
alembic current

# DB probe — robuste
python -c "
import os, psycopg

conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Vérifier existence schéma couche_b avant toute query
cur.execute('''
    SELECT schema_name FROM information_schema.schemata
    WHERE schema_name = 'couche_b'
''')
schema_exists = cur.fetchone()

if not schema_exists:
    print('SCHEMA couche_b ABSENT — état pré-MRD-1 ou branche fraîche')
    print('STOP si milestone >= MRD-1 attendu en prod')
else:
    try:
        cur.execute('''
            SELECT 'dict_items'   AS t, COUNT(*)
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
            UNION ALL
            SELECT 'aliases',     COUNT(*)
            FROM couche_b.procurement_dict_aliases
            UNION ALL
            SELECT 'vendors',     COUNT(*) FROM public.vendors
            UNION ALL
            SELECT 'mercurials',  COUNT(*) FROM public.mercurials
            ORDER BY t
        ''')
        for r in cur.fetchall():
            print(r)
    except Exception as e:
        print('PROBE PARTIAL FAILURE:', e)
        print('STOP — poster au CTO avant de continuer')
        exit(1)

cur.execute('SELECT version_num FROM alembic_version')
print('alembic_db:', cur.fetchall())
conn.close()
"
```

### S3 — Vérification invariants critiques

```bash
python -c "
import os, psycopg, subprocess

conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

stop_required = False

# ── INV-05 / INV-08 : triggers legacy et hash chain ──────────────────
cur.execute('''
    SELECT trigger_name
    FROM information_schema.triggers
    WHERE trigger_schema = 'couche_b'
      AND event_object_table = 'procurement_dict_items'
      AND trigger_name IN (
        'trg_block_legacy_family_insert',
        'trg_block_legacy_family_update',
        'trg_dict_compute_hash',
        'trg_dict_write_audit'
      )
''')
found    = {r[0] for r in cur.fetchall()}
expected = {
    'trg_block_legacy_family_insert',
    'trg_block_legacy_family_update',
    'trg_dict_compute_hash',
    'trg_dict_write_audit'
}
missing = expected - found
if missing:
    print('ALERTE TRIGGERS MANQUANTS — INV-05/INV-08 VIOLÉS:', missing)
    stop_required = True
else:
    print('TRIGGERS : tous présents — INV-05/INV-08 OK')

# ── INV-09 : CASCADE (lire milestone courant pour interpréter) ────────
cur.execute('''
    SELECT tc.table_name, kcu.column_name, rc.delete_rule
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.referential_constraints rc
      ON rc.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema   = 'couche_b'
      AND rc.delete_rule    = 'CASCADE'
''')
cascades = cur.fetchall()
if cascades:
    print('CASCADE FK détectée (anomalie connue AVANT MRD-3) :', cascades)
    print('Si milestone >= MRD-3 → STOP immédiat')
else:
    print('CASCADE FK : aucune')
    print('Si milestone < MRD-3 → vérifier régression — CASCADE doit être présente')

# ── INV-13 : 51 seeds human_validated intouchables ────────────────────
try:
    cur.execute('''
        SELECT COUNT(*)
        FROM couche_b.procurement_dict_items
        WHERE human_validated = TRUE
          AND active = TRUE
    ''')
    count = cur.fetchone()[0]
    if count < 51:
        print(f'ALERTE INV-13 : seeds human_validated = {count} < 51 — STOP')
        stop_required = True
    else:
        print(f'INV-13 OK : {count} seeds human_validated')
except Exception as e:
    print(f'INV-13 non vérifiable (table absente ?) : {e}')

conn.close()

# ── INV-11 : alembic heads = 1 ────────────────────────────────────────
result = subprocess.run(
    ['alembic', 'heads'],
    capture_output=True, text=True
)
lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
if len(lines) == 1:
    print('ALEMBIC HEADS OK — 1 ligne :', lines)
else:
    print('ALERTE ALEMBIC HEADS — multiple ou vide :', lines)
    stop_required = True

# ── Verdict final ──────────────────────────────────────────────────────
if stop_required:
    print()
    print('═══════════════════════════════════')
    print('STOP REQUIS — ne pas continuer')
    print('Poster résultat complet au CTO')
    print('═══════════════════════════════════')
    exit(1)
else:
    print()
    print('S3 OK — invariants vérifiés — GO lecture mandat')
"
```

### S4 — Condition de démarrage

```
S0 échoue (variable manquante)       → STOP. Poster au CTO.
S3 produit exit(1)                   → STOP. Poster au CTO.
S3 : CASCADE avant MRD-3             → noter dans clôture. Continuer.
S3 : CASCADE absente avant MRD-3     → STOP. Régression non planifiée.
S3 : CASCADE présente après MRD-3    → STOP. Régression critique.
Tout OK                              → lire le mandat du milestone. GO.
```

---

## PARTIE 4 — PROTOCOLE MANDAT

Tout mandat doit contenir ces 10 blocs.
**Un mandat sans ces 10 blocs est invalide.**
L'agent refuse d'exécuter un mandat invalide et le signale au CTO
en utilisant le format STOP défini en Partie 7.

```
BLOC 1  — IDENTITÉ
          Nom canonique, milestone, émetteur, date validation CTO,
          commit hash de référence au moment de l'émission du mandat

BLOC 2  — CONTEXTE RÉEL
          Résultat S2 au moment de l'émission, alembic_version Railway,
          divergences connues entre local et Railway

BLOC 3  — PÉRIMÈTRE FERMÉ
          Liste exhaustive des fichiers autorisés (pas "et fichiers similaires")
          Liste exhaustive des tables autorisées
          Opérations autorisées par fichier/table

BLOC 4  — HORS SCOPE
          Liste exhaustive des fichiers interdits
          Liste exhaustive des tables interdites
          Concepts interdits dans ce milestone

BLOC 5  — PRÉ-REQUIS
          Conditions booléennes vraies avant démarrage
          Si une condition est fausse → STOP immédiat, ne pas commencer
          Si reprise après interruption : étape de reprise identifiée ici

BLOC 6  — SÉQUENCE
          Étapes numérotées.
          Chaque étape marquée [AUTO] ou [CHECKPOINT].
          [AUTO]       : l'agent exécute et continue sans attendre
          [CHECKPOINT] : l'agent s'arrête, poste le résultat,
                         attend GO CTO explicite avant de continuer
          Étape non marquée = [CHECKPOINT] par défaut.
          Signal STOP dans une étape [AUTO] = arrêt immédiat,
          poster, attendre, jamais auto-correction.

BLOC 7  — SIGNAUX STOP
          Liste fermée des conditions déclenchant un arrêt immédiat
          Format de post : voir Partie 7
          L'agent poste l'output brut exact, sans reformulation

BLOC 8  — DONE BINAIRE
          Cases à cocher : [ ] ou [x]
          Vrai ou faux uniquement
          Zéro interprétation, zéro "pratiquement done"
          Un seul item non coché = milestone NOT DONE

BLOC 9  — OUTPUTS ATTENDUS
          Liste exacte des fichiers à créer
          Liste exacte des fichiers à modifier
          Liste exacte des migrations à appliquer
          Tests attendus avec noms exacts

BLOC 10 — VALIDATION CTO
          Décisions humaines identifiées dans ce milestone
          L'agent ne prend aucune de ces décisions seul
          Format : "Décision N : [description] — attend GO CTO"
```

---

## PARTIE 5 — RÈGLE APPEND-ONLY

Une table est append-only **si et seulement si** elle est explicitement classée
append-only dans l'un de ces documents :

- `DMS_V4.1.0_FREEZE.md`
- un ADR signé AO
- un contrat de schéma documenté dans `docs/freeze/`

**La présence ou l'absence de colonnes `updated_at`, `modified_at` ou
équivalentes n'est pas un critère suffisant pour classifier une table
comme append-only.**

Un agent ne peut pas déduire le statut append-only d'une table à partir
de son schéma. Il doit trouver la classification dans les documents
ci-dessus. Si la classification est absente → poser la question au CTO,
ne pas supposer.

### Tables explicitement classées append-only à ce jour

```
couche_b.procurement_dict_audit_log   ← append-only
couche_b.taxo_proposals_v2            ← append-only sur events
public.score_history                  ← append-only
public.dict_collision_log             ← append-only
public.decision_history               ← append-only
public.elimination_log                ← append-only
public.audit_log                      ← append-only
public.submission_registry_events     ← append-only (INV-R3)
```

Toute autre table non listée ici = statut non défini = poser la question
au CTO avant toute opération de mutation.

---

## PARTIE 6 — RÈGLES HASH CHAIN

### 6.1 Où la hash chain est active

```
couche_b.procurement_dict_items ← trg_dict_compute_hash (BEFORE UPDATE)
couche_b.procurement_dict_items ← trg_dict_write_audit  (AFTER UPDATE)
```

### 6.2 Règle pour tout agent

```
Avant toute migration touchant procurement_dict_items :
  → Vérifier trg_dict_compute_hash présent
  → Vérifier trg_dict_write_audit présent
  → Si l'un est absent : STOP immédiat. Ne pas continuer.

Après toute migration touchant procurement_dict_items :
  → Re-vérifier les 2 triggers
  → Si l'un est absent : ne pas merger. Poster au CTO.
```

### 6.3 Test obligatoire dans toute migration touchant le dictionnaire

```python
def test_hash_chain_triggers_present(db_conn):
    """
    Obligatoire dans toute migration touchant
    couche_b.procurement_dict_items.
    Echec = merge interdit.
    """
    cur = db_conn.cursor()
    cur.execute("""
        SELECT trigger_name
        FROM information_schema.triggers
        WHERE trigger_schema       = 'couche_b'
          AND event_object_table   = 'procurement_dict_items'
          AND trigger_name IN (
            'trg_dict_compute_hash',
            'trg_dict_write_audit'
          )
    """)
    found = {r[0] for r in cur.fetchall()}
    assert 'trg_dict_compute_hash' in found, \
        "HASH CHAIN PERDUE — trg_dict_compute_hash absent — STOP"
    assert 'trg_dict_write_audit' in found, \
        "AUDIT TRAIL PERDU — trg_dict_write_audit absent — STOP"
```

---

## PARTIE 7 — RÈGLES PAR TYPE D'AGENT

### Critère de sélection

| Tâche | Agent recommandé | Justification |
|---|---|---|
| Migration Alembic + tests associés | Claude Sonnet | Raisonnement long, cohérence multi-fichiers |
| Script ponctuel < 50 lignes | Claude Haiku | Rapide, périmètre borné strict |
| Refactoring multi-fichiers | Deepseek V3 | Périmètre liste exhaustive obligatoire |
| Complétion inline IDE | GitHub Copilot | Jamais migrations sans surveillance CTO |

### Contraintes par agent

| Agent | Contrainte spécifique |
|---|---|
| **Claude Sonnet** | Mandat doit imposer "output brut uniquement, zéro explication non demandée" |
| **Claude Haiku** | Mandat doit avoir zéro zone grise — tout cas d'ambiguïté prévu et borné explicitement |
| **Deepseek V3** | Périmètre fichiers = liste exhaustive — jamais "et fichiers similaires" |
| **GitHub Copilot** | Accès migrations Alembic interdit sans surveillance CTO explicite et continue |

### Règle universelle tous agents

```
Signal STOP = arrêt physique immédiat.
L'agent poste l'output brut et attend le CTO.
L'agent ne tente jamais de résoudre un signal STOP seul.
L'agent ne reformule jamais un output brut avant de le poster.
```

### Format standard de post STOP

```
🛑 SIGNAL STOP — [NOM_SIGNAL]
Milestone    : MRD-N
Étape        : N/M  [AUTO ou CHECKPOINT]
Timestamp    : YYYY-MM-DD HH:MM UTC

CAUSE :
[description factuelle en 1-3 lignes maximum]

OUTPUT BRUT :
[output exact de la commande qui a déclenché le STOP — non reformulé]

ÉTAT SYSTÈME AU MOMENT DU STOP :
git branch   : [valeur]
alembic heads: [valeur]
dernière action complétée : [étape N-1]

QUESTION AU CTO :
[une seule question, binaire si possible]

EN ATTENTE DE GO. Aucune action prise.
```

---

## PARTIE 8 — REGISTRE DES PIÈGES CONNUS

| # | Piège | Manifestation historique | Règle de protection | Statut |
|---|---|---|---|---|
| P-01 | Taxonomie imposée avant corpus | m7_2 : 15 domaines créés avant classification réelle | INV-07 : taxonomie toujours après analyse corpus | CLOS MRD-0 |
| P-02 | Migration sans downgrade() | Plusieurs M7 sans rollback réel | INV-10 : downgrade() obligatoire et testé | ACTIF — surveiller |
| P-03 | DB en avance sur repo | m7_4a présente Railway, absente repo | S2 : alembic heads + alembic current avant tout mandat | MITIGÉ |
| P-04 | CASCADE sur mémoire terrain | aliases → CASCADE détecté audit | INV-09 cible MRD-3 | ACTIF — anomalie connue |
| P-05 | birth_* lié à taxonomie mutable | birth_domain_id/family_l2_id couplés | birth_* sur dimensions stables uniquement | ACTIF — surveiller |
| P-06 | Hash chain silencieusement perdue | Triggers absents après migration | Test obligatoire Partie 6.3 sur toute migration dict | MITIGÉ |
| P-07 | Agent improvise sur signal STOP | Agent contournait recherches vides | STOP = arrêt physique, format Partie 7, jamais interprétation | MITIGÉ |
| P-08 | Stash WIP non committé | 7 stash entries dont WIP M7 actif | S2 : `git stash list` systématique | MITIGÉ |
| P-09 | Branche agent fantôme | 4 branches copilot/* dans origin | Jamais merger branche agent sans audit CTO complet | ACTIF — surveiller |
| P-10 | LLM inventant codes hors liste | Phase A : 77.9% flagged | INV-06 : liste fermée + raw LLM conservé | MITIGÉ |
| P-11 | Agent lit état avant loi | Ordre de lecture inversé | Hiérarchie Partie 0 imposée, S1 non sautée | MITIGÉ |
| P-12 | Milestone partiellement exécuté | Interruption réseau Mali | Partie 11 : protocole reprise | MITIGÉ |

**Légende statut :**
```
CLOS      : correction mergée, impossible en prod actuelle, surveillance passive
MITIGÉ    : règle en place, risque réduit, vérification active à chaque session
ACTIF     : peut se reproduire, surveillance maximale, signaler toute détection
```

---

## PARTIE 9 — FORMAT DE CLÔTURE MILESTONE

Fichier à créer : `docs/audits/MRD{N}_RESULT.md`

```markdown
---
milestone            : MRD-N
nom_canonique        : [nom exact du mandat]
date_utc             : YYYY-MM-DD HH:MM UTC
décideur             : AO
commit_hash          : [hash complet]
tag_git              : mrd-N-done
alembic_head         : [valeur exacte après merge]
---

## Counts Railway post-merge

| table | count |
|---|---|
| dict_items (active) | N |
| aliases | N |
| vendors | N |
| mercurials | N |

## Invariants

| Invariant | Statut | Commentaire |
|---|---|---|
| INV-01 | PASS \| FAIL \| N/A | [justification si FAIL ou N/A] |
| INV-02 | PASS \| FAIL \| N/A | |
| INV-03 | PASS \| FAIL \| N/A | |
| INV-04 | PASS \| FAIL \| N/A | |
| INV-05 | PASS \| FAIL \| N/A | |
| INV-06 | PASS \| FAIL \| N/A | |
| INV-07 | PASS \| FAIL \| N/A | |
| INV-08 | PASS \| FAIL \| N/A | |
| INV-09 | ANOMALIE_CONNUE (avant MRD-3) \| PASS (après MRD-3) \| RÉGRESSION | |
| INV-10 | PASS \| FAIL \| N/A | |
| INV-11 | PASS \| FAIL | |
| INV-12 | PASS \| FAIL \| N/A | |
| INV-13 | PASS \| FAIL \| N/A | |

**Règle** : un seul FAIL non justifié = merge interdit.
N/A obligatoirement justifié en commentaire.

## Hash chain

```
trg_dict_compute_hash : PRÉSENT | ABSENT
trg_dict_write_audit  : PRÉSENT | ABSENT
```

## Cascade FK

```
avant MRD-3 : CASCADE présente (anomalie connue OK) | CASCADE absente (STOP — régression)
après MRD-3 : CASCADE absente (INV-09 OK) | CASCADE présente (STOP — régression)
```

## Outputs produits

| Type | Fichier | Opération |
|---|---|---|
| migration | alembic/versions/0NN_xxx.py | créé |
| script | scripts/xxx.py | créé \| modifié |
| test | tests/test_xxx.py | créé \| modifié |
| doc | docs/xxx.md | créé \| modifié |
| supprimé | [chemin] | supprimé |

## Résultats tests

```
pytest : N passed / N failed / N skipped
coverage delta : +N% | N/A
```

## Statut

```
DONE    : tous les items BLOC 8 cochés, tous invariants PASS ou N/A justifié
NOT DONE: [item non coché ou FAIL non justifié]
```
```

---

## PARTIE 10 — TABLEAU DE VÉRITÉ MILESTONES

```
Milestone  Head Alembic après merge   Statut
─────────────────────────────────────────────
M0         035                        référence baseline
M0B        036_db_hardening
M1B        037_audit_hash_chain
M3         038_seed_geo_master_mali
M4         039_seed_vendors_mali
M5         040_mercuriale_ingest
M6         041_procurement_dictionary
M8         042_market_surveys
M10A       043_extraction_jobs_async
M11        044_ingestion_real_schema
M14        045_evaluation_documents
M16A       046_submission_registry
M16B       047_committee_seal_complete
```

**Invariant absolu** : `alembic heads` → exactement 1 ligne après chaque merge.
Toute déviation = STOP avant merge.

---

## PARTIE 11 — PROTOCOLE REPRISE APRÈS INTERRUPTION

Déclenché quand S2 révèle un état intermédiaire :
- migrations partielles (alembic current ≠ alembic heads)
- branche non mergée avec commits présents
- fichiers modifiés non commités (`git diff` non vide)
- stash WIP actif lié au milestone courant

### Procédure

```
1. L'agent NE CONTINUE PAS sans validation CTO

2. L'agent poste immédiatement :
   - git status (output complet)
   - git log --oneline -5
   - git stash list
   - alembic heads
   - alembic current
   - résultat S2 complet
   - dernière étape BLOC 6 dont l'agent est certain qu'elle est complète

3. Le CTO décide entre deux options uniquement :
   ROLLBACK  : revenir à un état propre connu
   REPRISE-N : reprendre à l'étape N du BLOC 6

4. Si ROLLBACK :
   git checkout main
   alembic downgrade -1   (si migration partiellement appliquée)
   git branch -D feat/mrd-N-xxx
   Relancer depuis S0.

5. Si REPRISE-N :
   Le mandat est amendé par le CTO avec BLOC 5 mis à jour :
   "Reprise depuis étape N — étapes 1 à N-1 déjà complètes"
   L'agent repart de S0 avec le mandat amendé.

6. L'agent ne devine jamais l'étape de reprise seul.
   L'agent ne tente jamais de compléter une migration partiellement
   appliquée sans GO CTO explicite.
```

---

## PARTIE 12 — PRINCIPE DIRECTEUR

Ce principe est le critère de dernier recours quand aucune règle
ne couvre un cas ambigu. L'agent se pose la question :

> *"Est-ce que cette action reflète exactement le réel ou le construit ?"*

Si la réponse est "construit" → ne pas faire. Poster au CTO.

```
DMS part du réel. Construit sur le réel. Mesure contre le réel.
Chaque agent exécute. Le CTO décide.
La donnée ne ment pas. Le code doit la refléter exactement.
La hash chain prouve. L'audit rappelle. La mémoire dure.
```

---

## CHECKSUMS DE VÉRIFICATION

```
SHA256 fichier : [GÉNÉRÉ APRÈS COMMIT]
SHA256 commit  : [GÉNÉRÉ APRÈS COMMIT]
Date hash      : [GÉNÉRÉE APRÈS COMMIT]

Commande de vérification :
  sha256sum docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md

Tout amendement → DMS_ORCHESTRATION_FRAMEWORK_V1.1_PATCH.md
Ce fichier n'est plus jamais modifié après hash.
```


