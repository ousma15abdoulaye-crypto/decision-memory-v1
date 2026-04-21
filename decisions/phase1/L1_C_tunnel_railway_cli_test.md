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

- [x] P1+P2+P3 OK → procéder ouverture tunnel
- [ ] L'un des 3 KO → documenter procédure d'install/auth

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

1. Télécharger PostgreSQL Windows binaries (https://www.postgresql.org/download/windows/)
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

| SLO cible                            | Mesure | Conforme ? |
| ------------------------------------ | ------ | ---------- |
| SELECT 1 latence < 500ms (cible pilote) | N/A    | N/A        |
| Tunnel stable durant 3 requêtes      | N/A    | N/A        |

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

**Fin L1-C.**
