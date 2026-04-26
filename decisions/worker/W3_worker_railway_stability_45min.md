# W3 — Test stabilité worker Railway 45+ min

**Statut** : ⚠️ **INCONCLUSIF / NON RECEVABLE**  
**Date** : 2026-04-23  
**Auteur** : Agent (session P3.4-INFRA-STABILIZATION)  
**Branche** : `chore/p3-4-infra-stabilization`

---

## Résumé exécutif

**Verdict** : ⚠️ **W3 INCONCLUSIF** — Test interrompu, données partielles non exploitables.

**Observations** :
- 66/66 pings HTTP 200 (100% succès sur échantillon partiel)
- Aucun timeout DB visible
- **Gap de 12 minutes** inexpliqué (08:48→09:00)
- Latences non mesurées (erreur parsing `bc`)
- Run incomplet : **66/100 pings** au lieu de 100

**Conclusion** : Aucun verdict PASS/FAIL sur Option C à ce stade.

**Recommandation** : **W3-bis requis** avec harness corrigé et environnement non suspendable.

---

## Contexte

**Objectif W3** : Valider stabilité longue durée (50 min continues) du worker Railway pour confirmer qu'Option C lève le blocage infra Phase 1/2.

**Question centrale** : Option C résout-elle les déconnexions Railway ~15 min observées en L1-D-bis ?

---

## Protocol exécuté

### Configuration

**Service** : `dms-db-worker-production.up.railway.app`  
**Endpoints** : `GET /db/ping`, `GET /db/info`  
**Durée cible** : 50 minutes  
**Intervalle** : 1 ping toutes les 30 secondes (100 pings attendus)

### Exécution

**Timestamp début** : `2026-04-23 08:15:44 UTC`  
**Timestamp fin** : `2026-04-23 09:06:04 UTC`  
**Durée réelle** : ~50 minutes  
**Pings exécutés** : **66/100** (incomplet)

**Script** : Bash + curl + sleep  
**Environnement** : Windows Git Bash

---

## Résultats observés

### Données quantitatives

| Métrique                    | Résultat observé     | Cible W3         | Statut       |
|-----------------------------|----------------------|------------------|--------------|
| **Pings exécutés**          | 66/100 (66%)         | 100/100          | ❌ Incomplet  |
| **Taux succès HTTP 200**    | 66/66 (100%)         | ≥ 98%            | ✅ (partiel)  |
| **Timeouts DB**             | 0                    | 0                | ✅           |
| **Latence mesurée**         | Non exploitable      | p95 < 150ms      | ❌ Données invalides |
| **Continuité session**      | Gap 12 min détecté   | Aucune interruption | ❌ **Échec critique** |

### Chronologie des événements

```
08:15:44  Test démarré
08:20:45  Ping #10 + /db/info OK
08:26:18  Ping #20 + /db/info OK
08:31:52  Ping #30 + /db/info OK
08:37:26  Ping #40 + /db/info OK
08:43:10  Ping #50 + /db/info OK
08:48:12  Ping #60 OK — DERNIER AVANT GAP
          ⚠️ [GAP 12 MINUTES — AUCUN PING]
09:00:21  Ping #61 OK — REPRISE + /db/info
09:05:29  Ping #66 OK — DERNIER
09:06:04  Test terminé (exit code 0)
```

**Gap critique** : Entre `08:48:12` et `09:00:21`, **aucune activité enregistrée** (12 minutes).

### Problèmes techniques identifiés

**1. Gap de 12 minutes inexpliqué**

Hypothèses :
- Suspension système Windows (veille/hibernation)
- CPU throttling/freeze processus bash
- Problème réseau local prolongé
- Script sleep() bloqué

Impact : **Invalide le critère de continuité W3**.

**2. Latences mesurées = 0 ms**

```csv
2026-04-23T08:15:44Z,/db/ping,200,0
2026-04-23T08:16:17Z,/db/ping,200,0
...
```

Cause : Commande `bc` échouée silencieusement dans Git Bash Windows.

```bash
latency_ms=$(echo "$latency_sec * 1000" | bc 2>/dev/null || echo "0")
```

Toutes les latences tombent sur le fallback `echo "0"`.

Impact : **Aucune donnée de latence exploitable**.

**3. Run incomplet (66/100 pings)**

Calcul attendu : 50 min / 30 sec = 100 pings  
Pings exécutés : 66

Cause probable : Gap de 12 min a consommé ~24 cycles (12*60/30=24), restant = 100-24=76, mais seulement 66 enregistrés.

Impact : **Échantillon insuffisant pour validation statistique**.

### Logs Railway

**Capture logs** : Processus `railway logs --follow` terminé prématurément (exit code 0), fichier vide.

Impact : **Aucune donnée logs Railway pour analyse reconnexions/erreurs**.

---

## Analyse des causes

### Hypothèse principale : Suspension système Windows

**Indice 1** : Gap exactement 12 minutes (durée typique veille partielle Windows).

**Indice 2** : Script bash en foreground sans mécanisme anti-suspension.

**Indice 3** : Environnement Git Bash Windows (non serveur, laptop/desktop).

### Défauts du harness de test

**1. Parsing latence fragile**

Dépendance `bc` non vérifiée → fallback silencieux vers 0.

**2. Absence de heartbeat/logging**

Pas de timestamp fichier intermédiaire pour détecter freeze.

**3. Environnement non dédié**

Test long sur poste de travail Windows = risque suspension.

---

## Données exploitables (limitées)

### Ce que W3 confirme partiellement

✅ **Connectivité worker Railway fonctionnelle** :
- 66 pings consécutifs HTTP 200 sans erreur DB
- Aucun timeout `connect_timeout=5s` déclenché

✅ **Endpoint `/db/info` accessible** :
- 6 requêtes metadata OK (pings 10, 20, 30, 40, 50, 61)

✅ **Aucune erreur HTTP** :
- 0 code 401/500/503 observé
- Authentification bearer stable

### Ce que W3 ne prouve PAS

❌ **Stabilité continue 50 min** : Gap de 12 min invalide le critère.

❌ **Latence stable** : Données latence inexploitables.

❌ **Absence de reconnexions DB** : Logs Railway non capturés.

❌ **Viabilité sessions 45+ min** : Test incomplet ne répond pas à la question centrale.

---

## Décision

### Statut W3

**W3 = INCONCLUSIF / NON RECEVABLE**

Le run ne peut pas servir de base à un verdict PASS/FAIL sur Option C :
- Interruption 12 min = échec critère continuité
- Latences non mesurées = pas de validation performance
- Logs Railway absents = pas de validation absence reconnexions
- 66/100 pings = échantillon statistiquement insuffisant

### Verdict Option C

**Aucun verdict à ce stade.**

Les observations partielles (66 pings HTTP 200) sont **encourageantes mais non concluantes**.

---

## Recommandation CTO

### W3-bis requis

**Objectif** : Re-exécuter test stabilité 50 min avec harness corrigé.

**Corrections obligatoires** :

1. **Fix parsing latence** :
   ```bash
   # Avant: bc (absent Windows)
   latency_ms=$(echo "$latency_sec * 1000" | bc 2>/dev/null || echo "0")
   
   # Après: awk (portable)
   latency_ms=$(echo "$latency_sec" | awk '{print $1 * 1000}')
   ```

2. **Environnement non suspendable** :
   - Exécution sur serveur Linux/VM dédiée (pas laptop Windows)
   - Ou désactiver veille Windows + keep-alive réseau pour durée test

3. **Heartbeat logging** :
   ```bash
   echo "$(date +%s)" > /tmp/W3_heartbeat.txt  # Chaque ping
   ```

4. **Logs Railway robustes** :
   ```bash
   railway logs --service dms-db-worker --follow --tail 1000 > W3_logs.txt 2>&1 &
   LOGS_PID=$!
   # Vérifier périodiquement que le processus tourne
   ```

5. **Validation post-run** :
   - Vérifier gaps timestamps (max toléré : 60s entre pings)
   - Vérifier 100 pings exécutés
   - Vérifier logs Railway 50 min capturés

### Timeline W3-bis

- **Setup harness corrigé** : 20 min
- **Exécution test** : 50 min (non interruptible)
- **Analyse + rapport** : 30 min

**Total** : ~1h40

**Pré-requis** : Environnement d'exécution stable validé (pas de suspension possible).

---

## Annexe : Dataset brut (partiel)

**Fichier** : 72 lignes (1 header + 66 pings + 5 /db/info checks)

```csv
timestamp,endpoint,status_code,latency_ms
2026-04-23T08:15:44Z,/db/ping,200,0
2026-04-23T08:16:17Z,/db/ping,200,0
...
2026-04-23T08:48:12Z,/db/ping,200,0
[GAP 12 MINUTES]
2026-04-23T09:00:21Z,/db/ping,200,0
2026-04-23T09:00:21Z,/db/info,checked,
...
2026-04-23T09:05:29Z,/db/ping,200,0
```

**Statistiques** :
- Total lignes : 72
- Pings `/db/ping` : 66
- Checks `/db/info` : 6
- HTTP 200 : 66/66 (100%)
- HTTP autres : 0
- Latences valides : 0/66 (parsing échoué)

---

## Conclusion finale

**W3 run 1 = INCONCLUSIF.**

Les données partielles ne permettent pas de valider ou invalider Option C pour sessions longues 45+ min.

**Prochaine étape** : **W3-bis** avec harness corrigé et environnement stable.

**Aucun changement statut blocage infra** : Phase 1/2 reste en investigation.

---

**Statut** : ⚠️ **W3 NON RECEVABLE — W3-bis requis pour verdict définitif Option C**
