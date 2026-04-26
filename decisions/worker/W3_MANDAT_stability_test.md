# Mandat W3 — Test stabilité worker Railway 45+ min

**Émetteur** : CTO Principal  
**Date** : 2026-04-23  
**Branche** : `chore/p3-4-infra-stabilization`  
**Prérequis** : W2 VALIDÉ (POC déployé opérationnel)  
**Statut** : ✅ **GO CTO APPROUVÉ**

---

## Objectif

Valider la **stabilité longue durée** du worker Railway `dms-db-worker` sur session **50 minutes continues** pour confirmer qu'Option C lève le blocage infra Phase 1/2.

**Question centrale** : Option C résout-elle le problème des **déconnexions Railway observées en L1-D-bis** (~15 min) ?

---

## Contexte décisionnel

**Phase 1 (L1-D, L1-D-bis)** a démontré :
- `railway run` : DNS failure 100%
- `railway connect postgres` : déconnexions **~15 min**

**W2** a validé :
- Déploiement worker Railway réussi
- Connectivité PostgreSQL interne fonctionnelle
- Latence courte (p95=54ms sur 10 pings)

**W2 ne prouve PAS** :
- Stabilité au-delà de quelques secondes
- Absence de timeout/déconnexion 45+ min
- Viabilité pour sessions annotation longues

**W3 doit trancher** : Option C lève-t-elle le blocage ou le problème est-il plus profond ?

---

## Périmètre W3

### Fichiers autorisés

**Création** :
- `decisions/worker/W3_worker_railway_stability_45min.md` (rapport final)
- Scripts de test temporaires (non committés si jetables)

**Lecture seule** :
- `services/worker-railway/main.py`
- Logs Railway via `railway logs`

**Aucune modification code** : W3 est un mandat **test/observation uniquement**.

---

## Protocol de test W3

### Configuration

**Service** : `<DMS_DB_WORKER_URL>`  
**Endpoints testés** :
- `GET /db/ping` (avec auth bearer)
- `GET /db/info` (avec auth bearer)

**Token** : `WORKER_AUTH_TOKEN` est lu depuis l'environnement local agent et **ne doit apparaître ni dans le script commité, ni dans les logs, ni dans le rapport W3.**

**Durée cible** : **50 minutes** (marge au-delà de 45 min)

### Scénario de test

**Phase 1 — Ping continu 50 min** :
- 1 requête `/db/ping` toutes les **30 secondes**
- Durée : 50 min = **100 pings**
- Capture : latence, timestamp, codes HTTP, erreurs

**Phase 2 — Query metadata périodique** :
- 1 requête `/db/info` toutes les **5 minutes**
- Durée : 50 min = **10 queries**
- Capture : taille DB, version, erreurs

**Logs Railway** :
- Surveiller logs worker pendant toute la durée
- Détecter : reconnexions, erreurs psycopg, timeouts

### Métriques à capturer

| Métrique                     | Cible                      | Seuil échec              |
|------------------------------|----------------------------|--------------------------|
| **Taux de succès HTTP 200**  | ≥ 98% (max 2 échecs/100)   | < 95%                    |
| **Latence p95**              | < 150 ms (indicatif)       | Dégradation > 2x médiane |
| **Timeouts DB**              | 0                          | ≥ 1                      |
| **Reconnexions psycopg**     | 0                          | ≥ 1                      |
| **Erreurs réseau Railway**   | 0                          | ≥ 1                      |

### Critères de validation

**Critères primaires** (tous obligatoires) :
- ✅ 50 min tenues sans interruption
- ✅ Taux succès HTTP 200 ≥ 98%
- ✅ Aucun timeout DB
- ✅ Aucune erreur critique / reconnexion dans les logs Railway

**Critère secondaire** (indicatif) :
- ✅ Latence p95 stable, cible indicative `< 150 ms`

---

**PASS W3** si **tous les critères primaires** sont remplis + critère secondaire raisonnable.

**FAIL W3** si **un seul critère primaire échoue** :
- ❌ Déconnexion avant 50 min
- ❌ Timeout DB ≥ 1
- ❌ Taux succès < 95%
- ❌ Erreurs critiques réseau/DB dans logs
- ❌ Dégradation massive latence (> 2x médiane initiale soutenue)

---

## Livrables W3

### Rapport final : `decisions/worker/W3_worker_railway_stability_45min.md`

**Sections obligatoires** :

1. **Résumé exécutif** (3 lignes max)
   - PASS/FAIL W3
   - Option C lève/ne lève pas le blocage
   - Validation pour sessions longues

2. **Protocol exécuté**
   - Commandes utilisées
   - Durée effective
   - Timestamp début/fin

3. **Résultats quantitatifs**
   - Tableau métriques (taux succès, latence p50/p95/max, timeouts)
   - **Tableau synthétique + dataset brut suffisent** (pas de graphe requis)

4. **Logs Railway analyse**
   - Extrait logs pertinents
   - Reconnexions détectées (ou absence)

5. **Décision finale**
   - PASS/FAIL selon critères
   - Recommandation : adoption Option C / investigation supplémentaire

6. **Annexe : dataset brut**
   - CSV ou JSON des 100 pings (timestamp, latency_ms, status_code)

### Commit

**Commit 1** : Rapport W3 uniquement  
**Message** : `docs(worker): W3 stability test 50min — [PASS|FAIL] Option C`

---

## Exécution pratique

### Script de test

```bash
#!/bin/bash
# W3_test_stability_50min.sh

URL="<DMS_DB_WORKER_URL>"
# Token lu depuis env local — JAMAIS exposé dans script/logs/rapport
TOKEN="${WORKER_AUTH_TOKEN}"
DURATION_MIN=50
INTERVAL_SEC=30

echo "timestamp,endpoint,status_code,latency_ms,error" > W3_results.csv

start=$(date +%s)
end=$((start + DURATION_MIN * 60))
counter=0

while [ $(date +%s) -lt $end ]; do
    counter=$((counter + 1))
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Ping test
    response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        -H "Authorization: Bearer $TOKEN" \
        "$URL/db/ping")
    
    status=$(echo "$response" | tail -2 | head -1)
    latency=$(echo "$response" | tail -1 | awk '{print $1 * 1000}')
    
    echo "$ts,/db/ping,$status,$latency," >> W3_results.csv
    
    # Info test every 5 min (10 times total)
    if [ $((counter % 10)) -eq 0 ]; then
        curl -s -H "Authorization: Bearer $TOKEN" "$URL/db/info" > /dev/null
        echo "$ts,/db/info,checked,," >> W3_results.csv
    fi
    
    sleep $INTERVAL_SEC
done

echo "✅ Test completed: $counter pings over $DURATION_MIN minutes"
```

**Monitoring parallèle** :
```bash
railway logs --service dms-db-worker --follow > W3_railway_logs.txt
```

---

## Contraintes

- **Pas de modification code** : W3 observe l'existant
- **Pas de redéploiement** : tester le worker actuel (commit 8bda421f)
- **Session unique** : 1 seul test 50 min (pas de retry sauf échec technique local)
- **Logs Railway à capturer** : démarrer avant test, arrêter après
- **Token JAMAIS exposé** : lecture env local uniquement

---

## Timeline estimée

- **Setup script** : 10 min
- **Exécution test** : 50 min (non interruptible)
- **Analyse résultats** : 15 min
- **Rédaction rapport W3** : 20 min

**Total** : ~1h35

---

## Décision post-W3

### Si W3 PASS

**Conclusion** : Option C **validée comme remédiation infra recevable** et permet l'ouverture contrôlée de la suite du chantier.

**Actions** :
1. Adoption Option C pour sessions annotation longues
2. Synthèse sous-chantier Worker Railway
3. Décision ouverture W4 selon roadmap CTO

### Si W3 FAIL

**Conclusion** : Le problème est **plus profond** (DB Railway, réseau, ou plateforme)

**Actions** :
1. Investigation approfondie (support Railway ?)
2. Options alternatives (PostgreSQL externe, autre hébergeur)
3. Escalade CTO pour décision architecture

---

## Autorisation d'exécution

✅ **GO CTO APPROUVÉ** avec ajustements validés

**Restrictions levées** :
- Bash avec `sleep` + `curl` autorisé pour test longue durée
- Capture logs Railway via `railway logs` autorisée

**Agent** : Exécute W3 immédiatement.
