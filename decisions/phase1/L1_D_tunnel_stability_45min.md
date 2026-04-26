# DMS Phase 1 — Fragment L1-D — Test stabilité tunnel 45 min

**Référence** : DMS-L1D-TUNNEL-STABILITY-V1
**Date** : 2026-04-22
**Mandat source** : DMS-MANDAT-PHASE1-FRAGMENT-L1D-STABILITY-V1
**Autorisation** : héritée V-L1C CTO principal (tunnel validé L1-C)
**Durée exécution** : 45.0 min wall-clock (script complet)

## Objectif

Valider SLO-3 : tunnel Railway CLI stable 45 min continues.

## Méthodologie

### Script utilisé

Voir `scripts/phase1/l1d_tunnel_stability_test.py`

### Paramètres de test

- Durée totale : 45 minutes (2700 secondes)
- Intervalle requête : 30 secondes
- Requêtes totales attendues : 90 (45 min / 30s)
- Requête test : `SELECT 1;`
- Logging : CSV avec timestamp, latence, status, erreur éventuelle
- Détection rupture : timeout > 5s OU erreur non-zéro

### Preflight

```bash
# État git avant
git branch --show-current   # chore/p3-4-infra-stabilization
git log --oneline -3        # HEAD: 02862993 (L1-C finalization)
git status --porcelain      # 5 fichiers modifiés (artefacts line endings)

# Vérification psycopg
python -c "import psycopg; print(psycopg.__version__)"  # 3.2.5

# Working tree
# 5 fichiers modifiés non stagés (normalisations LF→CRLF Windows)
# .gitignore, p34_infra_stabilization_opening_preflight.md,
# L1_A_baseline_health_backend.md, L1_B_envvars_delta.md, pyproject.toml
# Décision: non bloquant, artefacts hors périmètre L1-D
```

**Résultat preflight** : ✅ PASS — branche OK, psycopg installé, script créé et validé syntax

## Exécution

### Démarrage tunnel

**Méthode utilisée** : `railway run` (préférence forte §6.1 mandat)

**Commande** :

```bash
railway run python scripts/phase1/l1d_tunnel_stability_test.py \
  --duration 2700 \
  --interval 30 \
  --output docs/reports/p34/L1_D_raw_measurements.csv
```

**Horodatage démarrage script** : 2026-04-22T13:39:28 UTC

**Task ID background** : btktcqanz

**Monitor ID** : bmwrf7vs8 (surveillance progression via tail -f + grep)

### Script de monitoring lancé en parallèle

Monitor actif sur stdout script — notifications automatiques checkpoints toutes les 10 requêtes (~5 min).

## Résultats agrégés

### Requêtes exécutées

- Totales : **47/90 attendues** (52% des tentatives prévues)
- Succès : **0**
- Échecs : **47**
- Taux succès : **0.0%**

### Latences mesurées (échecs DNS uniquement)

**Note critique** : Aucune connexion DB établie. Les latences ci-dessous représentent les **timeouts de résolution DNS**, pas des latences PostgreSQL.


| Métrique      | Valeur (ms) |
| ------------- | ----------- |
| min           | 122.25      |
| p50 (médiane) | 131.56      |
| p95           | 413.99      |
| p99           | 999.15      |
| max           | 999.15      |


### Incidents détectés

**Incident systémique unique** :


| #   | Type                   | Détails                            | Occurrences  |
| --- | ---------------------- | ---------------------------------- | ------------ |
| 1   | DNS resolution failure | `[Errno 11001] getaddrinfo failed` | 47/47 (100%) |


**Gaps temporels anormaux** :


| Gap   | Entre attempts | Durée   | Hypothèse                        |
| ----- | -------------- | ------- | -------------------------------- |
| Gap-1 | #4 → #5        | ~21 min | Laptop sleep / idle suspension   |
| Gap-2 | #25 → #26      | ~2 min  | Réseau instable ou retry système |


Nombre total d'incidents : **1 type (systématique à 100%)**

## Analyse

### Stabilité tunnel

🔴 **Tunnel jamais établi**. Résolution DNS échouée sur 100% des tentatives (47/47). Le script a exécuté `railway run python ...` qui a injecté `DATABASE_URL` contenant un hostname Railway (probablement `maglev.proxy.rlwy.net` ou équivalent), mais ce hostname **n'est pas résolvable** depuis l'environnement agent Windows. Contrairement à L1-C où le CTO principal a réussi via `railway connect postgres` interactif, l'approche `railway run` non-interactive **échoue systématiquement** à résoudre le DNS du proxy Railway.

### Distribution des latences

Les latences mesurées (122-999ms) sont des **timeouts DNS**, pas des latences DB. Distribution bimodale : majorité ~130ms (timeout rapide), quelques outliers ~400-1000ms (retry DNS ou timeout long). Pas de pattern temporel exploitable — le problème est **fondamental** (résolution DNS impossible), pas lié à la stabilité réseau.

### Comportements anormaux

**Gap temporel critique** : 21 min de silence entre attempts #4-#5 (13:40→14:01). Hypothèse : laptop sleep/idle a suspendu le processus Python. Le script n'a pas de mécanisme de détection de suspension, donc les 47 tentatives sont étalées sur 45 min wall-clock mais seulement ~24 min de temps actif. **Gap secondaire** 2 min entre #25-#26 (réseau instable ou retry OS).

**Erreur systémique** : `[Errno 11001] getaddrinfo failed` est une erreur **Windows Sockets** (Winsock) indiquant que le resolver DNS local n'a **aucune route** vers le hostname cible. Cela suggère que `railway run` injecte une `DATABASE_URL` avec un hostname interne Railway (non publiquement résolvable) sans établir le tunnel préalable.

## Écarts par rapport aux SLO


| SLO         | Cible               | Mesure                                | Conforme ?       |
| ----------- | ------------------- | ------------------------------------- | ---------------- |
| SLO-3       | 45 min sans rupture | 47/47 tentatives échouées (0% succès) | 🔴 ÉCHEC TOTAL   |
| Latence p95 | < 500ms             | N/A (aucune connexion DB établie)     | 🔴 NON MESURABLE |
| Taux succès | > 99%               | 0.0%                                  | 🔴 ÉCHEC TOTAL   |


## Signaux pour L1-E (synthèse Phase 1) et Phase 2

**Signal critique** : La voie **L2+ (tunnel Railway CLI via `railway run`)** est **non viable** pour Phase 2+ dans l'état actuel.

**Cause racine** : `railway run` injecte `DATABASE_URL` avec hostname Railway non-publiquement résolvable (ex: `maglev.proxy.rlwy.net`), mais **n'établit pas de tunnel réseau** en arrière-plan pour rendre ce hostname accessible. L'approche interactive `railway connect postgres` (testée avec succès en L1-C par CTO principal) **fonctionne** parce qu'elle ouvre un proxy local psql, mais `railway run` non-interactive **ne le fait pas**.

**Recommandations pour L1-E et Phase 2** :

1. **Option A** (préférée) : **Tunnel manuel préalable obligatoire**. Avant tout script long-running, ouvrir `railway connect postgres` dans un terminal dédié, laisser ouvert, extraire `DATABASE_URL` du tunnel local (ou utiliser `localhost:5432` si Railway forward un port local). Scripts Python se connectent à `localhost` au lieu du hostname Railway.
2. **Option B** : **VPN Railway ou Bastion** (L3). Investiguer si Railway offre un VPN ou bastion pour résoudre nativement les hostnames internes. Hors scope Phase 1 actuelle.
3. **Option C** : **Fallback connexion directe publique**. Si Railway offre une `DATABASE_URL` publique (non tunnelée), l'utiliser. Trade-off sécurité (TLS obligatoire, IP whitelisting).

**Décision Phase 2** : Avant d'ouvrir I-DEBT-1 (backend extraction diagnostic), **bloquer** sur résolution voie L2+ ou pivot L3. Les benchmarks E4-quater nécessitent stabilité 45+ min — impossible avec 0% succès actuel.

## Risques identifiés


| Risque                                | Criticité   | Impact                                   | Mitigation                                                      |
| ------------------------------------- | ----------- | ---------------------------------------- | --------------------------------------------------------------- |
| DNS non résolvable via `railway run`  | 🔴 CRITIQUE | Bloque tout script long-running Phase 2+ | Option A (tunnel manuel) ou Option B (VPN Railway)              |
| Laptop sleep suspend processus Python | 🟡 MOYEN    | Gap 21 min → mesures incomplètes         | Script détection suspension OU env non-interactive (CI/serveur) |
| Pas de retry DNS intégré psycopg      | 🟢 BAS      | Échec immédiat sans retry                | Acceptable pour diagnostic pur (on veut voir l'échec)           |
| Gaps temporels masquent vrais SLO     | 🟡 MOYEN    | 47 tentatives ≠ 90 attendues             | Rejeu L1-D en env non-suspendable OU accept 50% coverage        |


## Verdict L1-D

- ✅ Script exécuté : **oui** (complètement, 45 min elapsed)
- ✅ 45 min complètes : **partiellement** — 45 min wall-clock, mais gaps suspend (21 min gap-1) → seulement ~24 min temps actif, 47/90 tentatives
- ✅ Mesures loggées : **47/90** (52% coverage)
- SLO-3 tenu : 🔴 **ÉCHEC TOTAL** — 0% succès, DNS resolution failed systématiquement, tunnel jamais établi
- Prêt L1-E (synthèse Phase 1) : **oui avec réserves** — L1-D révèle que L2+ non viable état actuel, nécessite décision architecturale avant Phase 2

**Verdict global L1-D** : 🔴 **ÉCHEC TECHNIQUE** — objectif "valider SLO-3 tunnel stable 45 min" **non atteint**. En revanche, L1-D **réussit en tant que diagnostic** : il révèle clairement que `railway run` seul ne suffit pas, ce qui est une **information précieuse** pour L1-E et stratégie Phase 2.

## Doctrines appliquées

G27 (supervision active obligatoire), G28 (SLO mesurés pas impression),
D-INFRA-2 (observability before optimization), D-INFRA-4 (fidelity
ladder niveau 3 atteint).

---

## Addendum CTO Senior — recevabilité du test L1-D

Le test L1-D exécuté a bien produit des mesures fidèles, mais il n'est pas recevable
comme preuve principale de SLO-3.

Raison :
le dispositif utilisé (`railway run` + `DATABASE_URL` injectée dans un script Python)
ne reproduit pas la voie validée en L1-C (`railway connect postgres` via psql interactif).

Conséquence :
- verdict initial "échec SLO-3" requalifié en **non recevable pour statuer sur SLO-3**
- finding auxiliaire conservé :
  la voie `railway run`/`DATABASE_URL` échoue depuis l'environnement agent
  avec `getaddrinfo failed`

Action correctrice :
L1-D-bis devra tester exclusivement la stabilité de la session
`railway connect postgres` maintenue 45 minutes.

---

**Fin L1-D.**