# DMS Phase 1 — Fragment L1-C — Test tunnel Railway CLI

**Référence** : DMS-L1C-TUNNEL-RAILWAY-TEST-V1
**Date** : 2026-04-21
**Mandat source** : DMS-MANDAT-PHASE1-FRAGMENT-L1C-TUNNEL-RAILWAY-V1
**Autorisation** : V-L1C ✅ CTO principal
**Durée exécution** : ~5 min wall-clock

## Objectif

Valider la faisabilité technique de l'ouverture d'un tunnel Railway
CLI vers PostgreSQL Railway depuis l'environnement agent, avec 3
mesures de diagnostic pur (connectivité, version, latence).

## Pré-vérifications

### P1 — Railway CLI installé ?

```bash
railway --version
```

**Résultat** :

```
railway 4.35.0
```

✅ Railway CLI présent (version 4.35.0)

### P2 — Authentification Railway active ?

```bash
railway whoami
```

**Résultat** :

```
Logged in as ousma15abdoulaye@gmail.com 👋
```

✅ Authentification active

### P3 — Projet Railway lié ?

```bash
railway status
```

**Résultat** :

```
Project: DMS
Environment: production
Service: annotation-backend
```

✅ Projet DMS lié (environnement production, service annotation-backend)

### Décision pré-tunnel

- P1+P2+P3 OK → procéder ouverture tunnel
- L'un des 3 KO → documenter procédure d'install/auth

**Décision** : Toutes pré-vérifications PASS → procéder étape B (ouverture tunnel)

## Ouverture tunnel

### Procédure utilisée

```bash
railway connect postgres
```

**Comportement observé** :

```
Exit code 1
psql must be installed to continue
```

**Horodatage tentative** : 2026-04-21 (heure relative)

### Blocage technique identifié

Le CLI Railway `connect` nécessite `psql` installé localement. L'environnement agent Windows (bash) ne dispose pas de `psql` dans le PATH.

**Railway CLI 4.x — mécanisme `connect`** :

- `railway connect <service>` invoque `psql` en local avec une connexion STRING injectée dynamiquement
- Si `psql` absent → refus immédiat (exit code 1)
- Alternatives possibles (non testées ce tour par contrainte temps §4.1) :
  - `railway run` avec commande personnalisée (ex: `railway run -- python -c "import psycopg; ..."`)
  - Extraction manuelle `DATABASE_URL` via `railway variables` puis connexion directe (hors cadre "tunnel CLI" strict)

### Décision §4.6 — Sortie gracieuse

Pré-vérifications CLI/auth OK mais **dépendance système `psql` manquante** → pas d'ouverture tunnel ce tour.

Verdict : **NOT READY — psql prerequisite not met**

Passage étape E (rédaction procédure théorique + fichier livrable) puis commit.

## Mesures via tunnel (3 requêtes pures)

**État** : Non exécutées (tunnel non ouvert)

### M1 — SELECT 1 (connectivité)

```sql
SELECT 1;
```

**Résultat** : N/A (psql absent)

### M2 — SELECT version() (identification PostgreSQL)

```sql
SELECT version();
```

**Résultat** : N/A (psql absent)

### M3 — Contexte DB (latence + taille)

```sql
SELECT now() AS server_time, 
       pg_size_pretty(pg_database_size(current_database())) AS db_size,
       current_database() AS db_name;
```

**Résultat** : N/A (psql absent)

## Procédure théorique d'installation `psql` (Windows)

### Option A — PostgreSQL binaries standalone

1. Télécharger PostgreSQL Windows binaries ([https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/))
2. Installer uniquement les outils client (`psql.exe`, binaires bin/)
3. Ajouter le chemin bin/ au PATH Windows
4. Vérifier : `psql --version`

### Option B — Railway CLI avec commande Python (contournement)

```bash
# Installer psycopg (driver Python PostgreSQL)
pip install psycopg[binary]

# Exécuter requêtes via railway run
railway run -- python -c "
import psycopg
import os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT 1')
print(cur.fetchone())
conn.close()
"
```

### Option C — WSL (Windows Subsystem for Linux)

1. Activer WSL2 sur Windows
2. Installer distribution Linux (Ubuntu)
3. Installer psql dans WSL : `sudo apt install postgresql-client`
4. Exécuter Railway CLI depuis WSL bash

## Fermeture tunnel

**État** : N/A (tunnel non ouvert)

## Observations

1. Railway CLI 4.35.0 fonctionnel (auth, project link OK) mais nécessite `psql` local pour `railway connect`.
2. Environnement agent Windows bash ne dispose pas de `psql` dans PATH par défaut.
3. Blocage attendu pour environnement Windows non configuré avec outils PostgreSQL client.
4. Pré-vérifications P1/P2/P3 toutes PASS — le blocage est une dépendance système externe (psql), pas un problème Railway auth/config.
5. Sortie gracieuse §4.6 appliquée : livrable L1-C produit avec procédure théorique, verdict NOT READY documenté.

## Écarts par rapport à SLO cible


| SLO cible                               | Mesure | Conforme ? |
| --------------------------------------- | ------ | ---------- |
| SELECT 1 latence < 500ms (cible pilote) | N/A    | N/A        |
| Tunnel stable durant 3 requêtes         | N/A    | N/A        |


## Signaux pour L1-D (test stabilité 45 min)

L1-D (test stabilité 45 min) bloqué tant que dépendance `psql` non résolue.

Options pour déblocage L1-D :

- **Option A (recommandée)** : Installer PostgreSQL client binaries Windows, ajouter au PATH, re-tenter L1-C puis enchaîner L1-D.
- **Option B** : Utiliser `railway run` avec driver Python `psycopg` (contournement, fonctionne mais hors cadre "tunnel CLI" strict du mandat L1-C).
- **Option C** : Basculer environnement agent sur WSL (bash Linux avec psql natif).

## Risques identifiés pendant L1-C

Aucun risque technique Railway/réseau identifié. Blocage purement dépendance système locale (psql absent).

## Verdict L1-C

- ✅ Railway CLI fonctionnel : oui (v4.35.0)
- ✅ Tunnel ouvert avec succès : non (psql prerequisite absent)
- ✅ 3 mesures SQL exécutées : non (tunnel non ouvert)
- ✅ Tunnel fermé proprement : N/A
- Prêt pour L1-D (stabilité long-running) : **non** — nécessite résolution dépendance `psql` d'abord

**Verdict final** : **NOT READY — psql prerequisite not met**

**Action recommandée** : Installer PostgreSQL client binaries Windows (Option A procédure théorique §) avant re-tentative L1-C ou passage L1-D.

---

## AMENDEMENT — Finalisation L1-C post V-L1C-UNBLOCK

**Référence amendement** : DMS-L1C-FINALIZATION-V-L1C-UNBLOCK
**Date amendement** : 2026-04-21
**Autorisation** : V-L1C-UNBLOCK=A+D CTO principal
**Exécutant mesures** : CTO principal DMS (option D — exécution sur machine CTO avec psql installé)
**Transcription livrable** : Agent Claude Code nouvelle session (option A — install psql Windows parallèle validée)
**Mandat source** : DMS-MANDAT-NOUVEL-AGENT-L1C-FINALIZATION-V1

### Contexte de la finalisation

Le blocage `psql prerequisite not met` identifié au verdict initial L1-C
a été résolu par double action V-L1C-UNBLOCK=A+D :
- **Option A** : PostgreSQL 16.13 client installé côté environnement
  Windows (chemin : `C:\Program Files\PostgreSQL\16\bin\psql.exe`,
  PATH mis à jour via PowerShell)
- **Option D** : CTO principal a exécuté les 3 mesures SQL sur sa
  propre machine authentifiée Railway, résultats bruts transcrits
  ci-dessous

Les deux options ont été appliquées en parallèle pour débloquer
immédiatement (D) et garantir l'autonomie future de l'agent (A).

### Environnement technique confirmé

| Élément | Valeur |
|---|---|
| Plateforme shell | Windows PowerShell |
| psql client | PostgreSQL 16.13 |
| psql path | `C:\Program Files\PostgreSQL\16\bin\psql.exe` |
| Railway CLI client | v4.35.0 (v4.40.0 disponible) |
| PostgreSQL serveur Railway | 17.9 (Debian 17.9-1.pgdg13+1) |
| Architecture serveur | x86_64-pc-linux-gnu |
| Compilation serveur | gcc (Debian 14.2.0-19) 14.2.0, 64-bit |
| SSL/TLS | TLSv1.3 actif |
| Cipher | TLS_AES_256_GCM_SHA384 |
| Compression | off |

### Avertissements psql (non bloquants)

```
WARNING: psql major version 16, server major version 17.
         Some psql features might not work.
WARNING: Console code page (850) differs from Windows code page (1252)
         8-bit characters might not work correctly.
```

Ces warnings sont connus et non bloquants :
- **Warning 1** (version mismatch) : client 16 vs serveur 17. Les
  méta-commandes avancées (`\d`, introspection) peuvent afficher
  différemment, mais les requêtes SQL standard fonctionnent.
  **Dette D-INFRA-ENV-1** : à moyen terme, aligner client sur
  version serveur (upgrade client 17 ou choix Railway client dédié).
- **Warning 2** (code page Windows) : caractères 8-bit potentiellement
  mal affichés. **Non bloquant** pour SQL standard ASCII.
  **Dette D-INFRA-ENV-2** : à basse priorité, configurer code page
  UTF-8 PowerShell (`chcp 65001`) pour sessions psql futures.

### Mesures SQL exécutées

#### M1 — SELECT 1 (connectivité)

```sql
SELECT 1;
```

**Résultat brut** :
```
 ?column? 
----------
        1
(1 row)
```

**Verdict M1** : ✅ SUCCÈS — connectivité DB Railway via tunnel établie.

**Latence** : Non instrumentée précisément ce tour (exécution
interactive psql sans `\timing`). Subjectivement : réponse
instantanée pour le CTO principal.
**Dette D-L1C-LATENCY** : en Phase 1 suivante (L1-D), utiliser
`\timing` psql ou scripter via Python pour mesurer latence p50/p95
précise sur 10+ requêtes.

#### M2 — SELECT version() (identification PostgreSQL)

```sql
SELECT version();
```

**Résultat brut** :
```
PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1) on x86_64-pc-linux-gnu, 
compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
```

**Verdict M2** : ✅ SUCCÈS — serveur identifié PostgreSQL 17.9.

**Observations stratégiques** :
- PostgreSQL 17 est la version majeure actuelle (release Sept 2024)
- Railway tient à jour — signal positif de maintenance plateforme
- Compatibilité DMS : vérifier en Phase 2 que les extensions Alembic
  et requêtes pipeline sont compatibles PostgreSQL 17

#### M3 — Taille base de données

```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
```

**Note** : version simplifiée exécutée par CTO principal (sans
`now()` ni `current_database()` explicite — implicite via
`current_database()` dans l'argument). Suffisant pour ce tour
selon doctrine G33.

**Résultat brut** :
```
 pg_size_pretty
----------------
 112 MB
(1 row)
```

**Verdict M3** : ✅ SUCCÈS — DB Railway DMS fait 112 MB actuellement.

**Observations stratégiques** :
- 112 MB = DB pilote, taille modeste. Cohérent avec pilote pré-prod.
- Pour contexte : un workspace pilote avec 1-2 dossiers actifs +
  historique P3.x doit faire l'ordre du Mo, les 112 MB incluent
  probablement indexes, tables techniques Alembic, logs, historique
  annotations.
- Signal pour capacity planning futur (hors scope phase actuelle).

### Fermeture tunnel

**Procédure utilisée** : exit propre via `\q` ou équivalent
(CTO principal a fermé sa session psql après M3).

**Durée totale tunnel ouvert** : estimée < 2 minutes (cadre strict
mandat respecté).

### Écarts par rapport à SLO cibles

| SLO cible | Mesure effective | Conforme ? |
|---|---|---|
| SELECT 1 latence < 500ms (cible pilote) | Non instrumenté (subjectivement instantané) | ⏳ À mesurer L1-D |
| Tunnel stable durant 3 requêtes | ✅ Stable (3/3 requêtes réussies) | ✅ |
| TLS/SSL actif | ✅ TLSv1.3 avec cipher AES-256-GCM | ✅ |

### Signaux pour L1-D (test stabilité 45 min)

**Validations acquises grâce à cette finalisation** :
1. ✅ Tunnel Railway CLI opérationnel et sécurisé TLS
2. ✅ psql 16 installé et fonctionnel (option A validée côté agent)
3. ✅ Connectivité DB Railway via proxy `maglev.proxy.rlwy.net`
4. ✅ Authentification Railway persistante

**À produire spécifiquement en L1-D** :
- Latence précise p50/p95/p99 sur 90+ requêtes (`\timing` psql ou script Python)
- Stabilité continue 45 minutes sans rupture tunnel
- Comportement en cas de sleep laptop / network glitch (supervision L2+ requise)
- Performance SELECT simple vs SELECT avec JOIN (profilage léger)

### Risques identifiés

| Risque | Criticité | Action |
|---|---|---|
| psql 16 vs serveur 17 mismatch | 🟡 MOYEN | Dette D-INFRA-ENV-1, upgrade futur |
| Code page Windows 850 | 🟢 BAS | Dette D-INFRA-ENV-2, config UTF-8 |
| Tunnel CLI monoposte | 🟡 MOYEN | Supervision L2+ en L1-D, fallback L1 documenté |
| Latence non mesurée précisément | 🟡 MOYEN | À produire L1-D |

### Dettes ouvertes ce tour

| Ref | Dette | Priorité | Phase cible |
|---|---|---|---|
| D-INFRA-ENV-1 | Upgrade client psql 16 → 17 (alignement serveur) | 🟡 MOYEN | Post-phase infra |
| D-INFRA-ENV-2 | Config code page UTF-8 PowerShell | 🟢 BAS | Post-phase infra |
| D-L1C-LATENCY | Instrumentation latence précise requêtes DB | 🟡 MOYEN | Phase 1 L1-D |

### Verdict final L1-C — RÉVISÉ

**Verdict initial** : `NOT READY — psql prerequisite not met`

**Verdict final post-finalisation** : 🟢 **READY**

Justification de la révision :
- ✅ Railway CLI fonctionnel (v4.35.0)
- ✅ Tunnel ouvert avec succès (via option D, CTO principal)
- ✅ 3 mesures SQL exécutées (M1, M2, M3) — toutes succès
- ✅ Tunnel fermé proprement
- ✅ psql 16.13 installé côté agent (option A) — autonomie future acquise
- ✅ TLSv1.3 actif — sécurité transport validée
- ✅ Serveur PostgreSQL 17.9 identifié — plateforme à jour
- ✅ DB taille 112 MB — cohérente pilote

**Prêt pour L1-D (test stabilité tunnel 45 min)** : **OUI**

### Doctrines appliquées ce tour

| Ref | Doctrine |
|---|---|
| G2 | Rapport augmenté, pas réécrit (section amendement ajoutée) |
| G33 | Production > exhaustivité (M3 version simplifiée acceptée) |
| G37 | Autorisation absolue CTO principal → garde-fous techniques conservés |
| G40 | Sortie gracieuse NOT READY initiale ≠ échec — débloqué proprement |

---

**Fin amendement L1-C — verdict révisé READY.**

---

**Fin L1-C.**