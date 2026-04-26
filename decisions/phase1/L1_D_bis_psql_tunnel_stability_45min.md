# DMS Phase 1 — Fragment L1-D-bis — Test stabilité psql tunnel 45 min

**Référence** : DMS-L1D-BIS-PSQL-TUNNEL-STABILITY-V1
**Date** : 2026-04-22
**Mandat source** : DMS-MANDAT-L1D-BIS-PSQL-45MIN-V1
**Autorisation** : héritée V-L1C CTO principal (voie tunnel validée)
**Durée exécution** : ~15 min réels (rupture session avant terme)

## Contexte bref

Suite à la requalification de L1-D (non recevable pour SLO-3 car mécanisme `railway run` inadapté), L1-D-bis teste la stabilité **de la voie L1-C validée** : session `railway connect postgres` maintenue pendant 45 minutes avec requête simple toutes les 30 secondes.

**Objectif** : statuer de manière recevable sur SLO-3 (stabilité tunnel 45 min).

## Protocole exact exécuté

### Méthode

Commande bash inline (pas de script séparé) :

```bash
export PATH="$PATH:/c/Program Files/PostgreSQL/16/bin"
{ 
  echo "[L1-D-bis] Starting psql tunnel stability test at $(date -u)"
  for i in {1..90}; do
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    echo "[Iteration $i/90 at $timestamp]"
    echo "SELECT now() AS server_time, 1 AS ok;"
    sleep 30
  done
  echo "\q"
} | railway connect postgres 2>&1 | tee /tmp/l1d_bis_raw_output.log
```

### Détails techniques

- **Voie utilisée** : `railway connect postgres` (conforme L1-C)
- **Session** : unique session psql continue (pas de reconnexions)
- **Requête test** : `SELECT now() AS server_time, 1 AS ok;`
- **Intervalle** : 30 secondes
- **Cible** : 90 itérations (45 min)
- **psql version** : PostgreSQL 16.13 (client Windows)

### Limite méthodologique identifiée

Les lignes `echo "[Iteration ...]"` ont été **injectées dans stdin** du pipe et donc **envoyées à psql comme des commandes SQL**, générant des syntax errors sur chaque itération. Les `SELECT` valides ont probablement été exécutés entre les echo, mais **stdout psql n'apparaît pas dans les logs** (seul stderr capturé montre les erreurs).

**Impact** : impossible de confirmer visuellement les résultats SELECT, mais la session est restée active malgré les erreurs (psql continue après syntax error).

## Journal synthétique des itérations

### Période active

- **Début** : 2026-04-22T16:25:35Z
- **Fin (rupture)** : 2026-04-22T16:40:41Z
- **Durée réelle** : ~15 minutes (33% de la cible 45 min)

### Itérations observées

| Plage | Itérations | Observations |
|---|---|---|
| 1-31 | 31/90 | Erreurs syntax sur echo markers, session active |
| 32-90 | 0 (non atteintes) | Rupture session après iteration 31 |

**Total itérations** : 31/90 (34%)

### Horodatages clés

| Event | Timestamp | Notes |
|---|---|---|
| Démarrage session | ~16:25:35Z | `railway connect postgres` ouvert |
| Iteration 10 | 16:30:07Z | Session stable |
| Iteration 20 | 16:35:09Z | Session stable |
| Iteration 31 | 16:40:41Z | Dernière itération avant rupture |
| Rupture session | ~16:40:41Z | `server closed the connection unexpectedly` |

## Incidents observés

### Incident 1 — Erreurs syntax echo markers (non bloquant)

**Type** : Erreur méthodologique  
**Occurrences** : 31/31 itérations  
**Message** :
```
ERROR:  syntax error at or near "["
LINE 1: [Iteration N/90 at ...]
```

**Cause** : Les lignes `echo` bash ont été envoyées comme SQL à psql.

**Impact** : Logs pollués, stdout SELECT masqué, mais **session restée active** (psql continue après syntax error).

**Criticité** : 🟡 MOYEN — ne prouve pas l'échec des SELECT, mais rend l'audit visuel impossible.

### Incident 2 — Rupture session Railway (bloquant)

**Type** : Fermeture connexion côté serveur  
**Horodatage** : ~2026-04-22T16:40:41Z (après iteration 31, ~15 min)  
**Message exact** :
```
server closed the connection unexpectedly
	This probably means the server terminated abnormally
	before or while processing the request.
connection to server was lost
```

**Cause probable** :
- **Timeout inactivité Railway** : Le proxy `maglev.proxy.rlwy.net` ou PostgreSQL Railway peut avoir un timeout idle ~15 min sur sessions interactives
- **Policy Railway** : Railway peut limiter la durée des sessions `railway connect` non-production
- **Network glitch** : moins probable (message clair = serveur a fermé)

**Impact** : Test interrompu à 33% de la cible, **SLO-3 non atteignable**.

**Criticité** : 🔴 CRITIQUE — bloque validation SLO-3.

## Verdict SLO-3

🔴 **FAIL** — Session Railway psql **non stable sur 45 minutes**.

**Justification** :
1. Session rompue après ~15 min (33% de la cible)
2. Rupture côté serveur Railway (`server closed the connection unexpectedly`)
3. Aucune veille laptop détectée (timestamps réguliers toutes les 30s jusqu'à rupture)
4. Exit code 0 de la commande bash ne reflète pas l'échec psql (pipe masque l'erreur)

**Hypothèse technique** :
Railway impose probablement un **timeout idle ou durée max** sur les sessions `railway connect postgres` interactives. 15 minutes est cohérent avec une policy réseau "connexion interactive raisonnable" mais insuffisant pour benchmarks long-running (E4-quater cible).

## Recommandation courte pour L1-E

**Signal critique** : **Aucune voie L2 testée (L1-D `railway run`, L1-D-bis `railway connect`) n'a tenu 45 minutes**.

### Options stratégiques Phase 2

1. **Option A — VPN Railway ou connexion directe publique**
   - Investiguer si Railway offre `DATABASE_URL` publique (non tunnelée) avec TLS
   - Trade-off : sécurité (whitelist IP requis), latence potentielle
   - Avantage : pas de timeout idle

2. **Option B — Sessions courtes + reconnexion automatique**
   - Accepter timeout 15 min Railway
   - Scripts Phase 2 avec auto-reconnect toutes les 10 min
   - Trade-off : complexité, risque perte état session
   - Avantage : compatible infra actuelle

3. **Option C — Environnement dédié Railway (non-local)**
   - Déployer worker Python sur Railway même projet
   - Connexion interne `DATABASE_URL` (pas de tunnel CLI)
   - Trade-off : déploiement supplémentaire, coûts
   - Avantage : pas de timeout, latence optimale

**Décision requise CTO Senior** : Avant Phase 2, choisir voie finale. L1-E synthétisera findings L1-A→L1-D-bis et bloquera sur ce choix architectural.

## Métriques observées

| Métrique | Valeur | Conforme SLO-3 ? |
|---|---|---|
| Durée session | ~15 min | 🔴 NON (cible 45 min) |
| Itérations complétées | 31/90 | 🔴 NON (34%) |
| Ruptures session | 1 (à ~15 min) | 🔴 NON (cible 0) |
| Cause rupture | Serveur Railway fermeture | N/A |

## Doctrines appliquées

- **G40** : Sortie gracieuse sur rupture, FAIL propre documenté
- **G44** : Révélation empirique limite Railway CLI (timeout ~15 min)
- **G28** : SLO mesuré factuellement (pas d'impression)

## Limite du test reconnue

**Méthodologie imparfaite** (echo markers → SQL) rend audit visuel incomplet, mais **la rupture session à 15 min est indépendante** de cette limite et suffit pour conclure FAIL.

Un retry avec logging propre (sans echo dans stdin) ne changerait pas le verdict si Railway maintient sa policy timeout ~15 min.

---

**Fin L1-D-bis. Verdict SLO-3 : FAIL (rupture session 15 min, cible 45 min non atteinte).**
