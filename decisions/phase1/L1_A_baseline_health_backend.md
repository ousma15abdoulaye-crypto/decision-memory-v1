# DMS Phase 1 — Fragment L1-A — Baseline backend Railway

**Référence** : DMS-L1A-BASELINE-HEALTH-V1
**Date** : 2026-04-21
**Mandat source** : DMS-MANDAT-PHASE1-FRAGMENT-L1A-BASELINE-V1
**Durée exécution** : ~10 min wall-clock

## Objectif

Mesurer le comportement backend Railway au repos (sans charge) pour
établir une baseline de référence.

## Commandes exécutées

```bash
# Création dossier
mkdir -p decisions/phase1

# M1 - Baseline /health 20 requêtes
for i in $(seq 1 20); do
  curl -sS -o /dev/null \
    -w "%{http_code}|%{time_total}|%{time_connect}|%{time_starttransfer}\n" \
    https://dms-annotation-backend-production.up.railway.app/health
  sleep 6
done

# M2 - DNS backend
nslookup dms-annotation-backend-production.up.railway.app

# M3 - DNS PostgreSQL Railway
nslookup maglev.proxy.rlwy.net

# M4 - TCP ping (tenté PowerShell, permission refusée)
# Test-NetConnection -ComputerName maglev.proxy.rlwy.net -Port 35451
```

## Résultats mesurés

### M1 — Baseline `/health` 20 requêtes sur 2 min

**Commande type** :
```bash
for i in $(seq 1 20); do
  curl -sS -o /dev/null \
    -w "%{http_code}|%{time_total}|%{time_connect}|%{time_starttransfer}\n" \
    https://dms-annotation-backend-production.up.railway.app/health
  sleep 6
done
```

**Résultats** :

| # | HTTP code | time_total (s) | time_connect (s) | time_starttransfer (s) |
|---|---|---|---|---|
| 1 | 200 | 1.267619 | 0.325242 | 1.267483 |
| 2 | 200 | 1.001615 | 0.263775 | 1.001488 |
| 3 | 200 | 0.900817 | 0.157220 | 0.900648 |
| 4 | 200 | 0.928839 | 0.163113 | 0.928682 |
| 5 | 200 | 0.958926 | 0.156740 | 0.958683 |
| 6 | 200 | 0.877966 | 0.149689 | 0.877816 |
| 7 | 200 | 0.872318 | 0.156443 | 0.872086 |
| 8 | 200 | 0.884340 | 0.163793 | 0.884243 |
| 9 | 200 | 0.956690 | 0.162718 | 0.956452 |
| 10 | 200 | 1.005779 | 0.277019 | 1.005550 |
| 11 | 200 | 0.884207 | 0.143126 | 0.883761 |
| 12 | 200 | 0.898619 | 0.162130 | 0.898509 |
| 13 | 200 | 0.935173 | 0.161655 | 0.935081 |
| 14 | 200 | 0.954110 | 0.146606 | 0.953980 |
| 15 | 200 | 0.940580 | 0.161345 | 0.940368 |
| 16 | 200 | 0.883988 | 0.148228 | 0.883750 |
| 17 | 200 | 0.877041 | 0.141991 | 0.876329 |
| 18 | 200 | 0.919397 | 0.166726 | 0.919233 |
| 19 | 200 | 1.038875 | 0.294213 | 1.038497 |
| 20 | 200 | 1.090042 | 0.284473 | 1.089863 |

**Agrégats** (calculés manuellement sur time_total) :
- p50 time_total : 0.930s (médiane : 10e et 11e valeurs triées)
- p95 time_total : 1.090s (19e valeur triée)
- max time_total : 1.268s
- Taux de succès 200 : 20/20 (100%)

### M2 — Résolution DNS vers backend Railway

```bash
nslookup dms-annotation-backend-production.up.railway.app
```

**Résultat** :
```
Réponse ne faisant pas autorité :
Serveur :   dns.google
Address:  8.8.8.8

Nom :    dms-annotation-backend-production.up.railway.app
Address:  151.101.2.15
```

**Observation** : Résolution DNS réussie en < 100ms (estimé), une seule IP retournée (151.101.2.15).

### M3 — Résolution DNS vers PostgreSQL Railway

```bash
nslookup maglev.proxy.rlwy.net
```

**Résultat** :
```
Réponse ne faisant pas autorité :
Serveur :   dns.google
Address:  8.8.8.8

Nom :    maglev.proxy.rlwy.net
Address:  66.33.22.251
```

**Observation** : Résolution DNS réussie en < 100ms (estimé), une seule IP retournée (66.33.22.251).

### M4 — TCP ping / connectivité PostgreSQL Railway (sans auth)

**Commande tentée** :
```powershell
Test-NetConnection -ComputerName maglev.proxy.rlwy.net -Port 35451
```

**Résultat** :
```
Permission refusée (PowerShell bloqué en don't ask mode).
Mesure non exécutée (nice-to-have selon §5 mandat).
```

**Observation** : Outil bash équivalent (nc, tcping) non disponible en environnement Windows bash. Mesure reportée ou à exécuter ultérieurement via tunnel Railway CLI (L1-C).

## Observations

1. Backend Railway `/health` répond systématiquement HTTP 200 avec latence p95 de 1.09s — stable sur 20 requêtes, aucun échec.
2. time_total oscille entre 0.87s et 1.27s — variabilité modérée, potentiellement due à cold start ou latence réseau variable.
3. Résolution DNS backend et PostgreSQL Railway fonctionnelle sans erreur `getaddrinfo failed` (contrairement aux symptômes E4-ter documentés dans preflight).
4. TCP ping PostgreSQL non mesuré (outil manquant) — connectivité DB à valider en L1-C via tunnel Railway CLI.

## Écarts par rapport à SLO cible

| SLO cible | Mesure | Conforme ? |
|---|---|---|
| SLO-1 : /health p95 < 500ms | 1.09s | 🔴 NON CONFORME (2.2x limite) |

## Signaux pour Phase 2 / 3

- Latence `/health` au repos (1.09s p95) dépasse déjà SLO-1 sans charge d'extraction — investigation cold start Railway + dimensionnement nécessaire Phase 2.
- DNS stable ce tour (aucun `getaddrinfo failed`) — symptôme E4-ter possiblement intermittent ou lié à connectivité agent local antérieure.

## Verdict L1-A

- ✅ Mesures collectées : oui (M1, M2, M3 complètes ; M4 non exécutée)
- Baseline exploitable : oui (suffisante pour référence avant/après fix)
- Prêt pour L1-B : oui (inventaire env vars delta indépendant de ces mesures)

---

**Fin L1-A.**
