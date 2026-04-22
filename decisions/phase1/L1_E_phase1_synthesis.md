# DMS Phase 1 — Fragment L1-E — Synthèse Phase 1 I-DEBT-2

**Référence** : DMS-L1E-PHASE1-SYNTHESIS-V1
**Date** : 2026-04-22
**Mandat source** : DMS-MANDAT-L1E-PHASE1-SYNTHESIS-V1
**Autorité** : CTO principal DMS (pré-arbitrage C3 confirmé 2026-04-22)
**Statut** : 🟢 CLÔTURE PHASE 1 — synthèse opposable

---

## 1. Rappel du mandat Phase 1 et du contrat P3.4-INFRA-STABILIZATION

### Mandat Phase 1 — I-DEBT-2 (DB stable)

**Objectif** : Diagnostiquer et documenter la stabilité des voies d'accès à PostgreSQL Railway depuis l'environnement agent, en réponse aux échecs `getaddrinfo failed` récurrents observés en session E4-ter.

**Contrat P3.4** : Stabiliser l'infrastructure DMS (I-DEBT-1 backend extraction + I-DEBT-2 DB stable + I-DEBT-3 corpus sink) avant relance benchmark E4-quater. Phase 1 = diagnostic pur, pas d'implémentation correctrice.

**Périmètre Phase 1** : 6 fragments documentaires L1-A → L1-E (baseline, env vars, tunnel CLI, stabilité, synthèse).

**SLO cibles Phase 1** :
- **SLO-1** : `/health` backend Railway p95 < 500ms (cible pilote)
- **SLO-3** : Tunnel DB stable 45 min continues sans rupture

---

## 2. Synthèse L1-A → L1-D-bis

### L1-A — Baseline health backend Railway

**Objet** : Mesurer `/health` backend Railway sur 100 requêtes / 10 min depuis environnement agent.

**Résultats** :
- 100/100 requêtes réussies (HTTP 200)
- Latences : min 60ms, p50 651ms, p95 **1090ms**, max 1937ms
- Backend fonctionnel mais **lent** : p95 dépasse largement cible 500ms

**Verdict SLO-1** : 🔴 **ROUGE** (p95 = 1.09s, cible < 500ms)

**Finding** : Backend Railway répond correctement mais avec latence dégradée. Causes possibles : cold start Railway, dimensionnement CPU/RAM, overhead réseau, ou charge backend interne.

---

### L1-B — Delta env vars Railway vs local

**Objet** : Documenter les divergences de configuration env vars entre environnement agent local et backend Railway production.

**Résultats** :
- Aucune divergence critique détectée sur les variables essentielles (`MISTRAL_API_KEY`, `DATABASE_URL`, `LABEL_STUDIO_URL`)
- 4 dettes mineures tracées (formatage, redondances, nommage)

**Verdict** : ✅ Configuration Railway cohérente avec spécifications DMS V4.1

**Dettes ouvertes** :
- D-L1B-ENV-1 : Formatter env Railway via Terraform
- D-L1B-ENV-2 : Supprimer variables redondantes
- D-L1B-ENV-3 : Renommer `LABEL_STUDIO_HOST` → `LABEL_STUDIO_URL`
- D-L1B-ENV-4 : Documenter variables non-DMS héritées Railway

---

### L1-B-bis — Registre dette env vars

**Objet** : Formaliser les 4 dettes L1-B dans registre opposable.

**Verdict** : ✅ Registre créé, dettes tracées avec priorité/phase cible.

---

### L1-C — Test tunnel Railway CLI

**Objet** : Valider faisabilité ouverture tunnel `railway connect postgres` et exécuter 3 mesures SQL (M1 SELECT 1, M2 version, M3 taille DB).

**Résultats** :
- **Tentative initiale** : `psql prerequisite not met` (blocage environnement agent)
- **Finalisation CTO principal** (option V-L1C-UNBLOCK=A+D) :
  - PostgreSQL 16.13 client installé Windows
  - Tunnel ouvert avec succès (TLSv1.3, PostgreSQL 17.9, DB 112 MB)
  - 3 mesures SQL exécutées avec succès

**Verdict final L1-C** : ✅ **READY** — voie `railway connect postgres` validée avec psql client installé

**Observations** :
- Warning version mismatch (psql 16 vs serveur 17) non bloquant
- Autonomie agent acquise après install psql
- TLS/SSL actif (TLSv1.3 avec cipher AES-256-GCM)

---

### L1-D — Test stabilité tunnel via `railway run` (diagnostic auxiliaire)

**Objet** : Tester stabilité tunnel 45 min via mécanisme `railway run` + script Python + psycopg.

**Résultats** :
- 47 tentatives sur 90 attendues (52% coverage)
- **0% succès** : 47/47 échecs `[Errno 11001] getaddrinfo failed`
- Cause : `railway run` injecte `DATABASE_URL` avec hostname Railway non résolvable depuis environnement agent

**Verdict SLO-3** : ❌ **NON RECEVABLE** pour statuer sur SLO-3

**Requalification** (addendum CTO Senior) :
- Test L1-D exécuté fidèlement mais ne reproduit pas la voie validée L1-C
- Finding auxiliaire conservé : voie `railway run` non viable depuis environnement agent
- L1-D-bis requis pour test recevable SLO-3

---

### L1-D-bis — Test stabilité psql tunnel 45 min (recevable)

**Objet** : Tester stabilité exclusive de la voie L1-C validée (`railway connect postgres` + psql interactif) sur 45 min.

**Résultats** :
- Session ouverte avec succès (~16:25:35Z)
- 31 itérations exécutées sur 90 attendues (34%)
- **Rupture session** après ~15 min : `server closed the connection unexpectedly`
- Cause : Timeout Railway côté serveur (~15 min sur sessions `railway connect postgres`)

**Verdict SLO-3** : 🔴 **FAIL** — Session Railway psql **non stable 45 minutes**

**Finding critique** : Railway ferme les sessions `railway connect postgres` après ~15 min (policy timeout idle ou durée max sessions interactives). Incompatible avec benchmarks long-running (E4-quater cible 45+ min).

---

## 3. Verdicts SLO mesurés

| SLO | Cible | Mesure | Verdict | Référence |
|---|---|---|---|---|
| **SLO-1** | `/health` p95 < 500ms | p95 = **1090ms** | 🔴 **ROUGE** | L1-A |
| **SLO-3** | Tunnel stable 45 min | Rupture à **~15 min** | 🔴 **FAIL** | L1-D-bis (recevable) |

**Synthèse** : Aucun des 2 SLO Phase 1 n'est atteint dans l'état actuel de l'infrastructure.

---

## 4. Dettes et findings consolidés

### Dettes Phase 1 ouvertes

| Ref | Dette | Criticité | Phase cible |
|---|---|---|---|
| **D-L1A-HEALTH-LATENCY** | `/health` backend lent (p95 1.09s) | 🟡 MOYEN | Phase 2 I-DEBT-1 |
| D-L1B-ENV-1 | Formatter env vars Railway via Terraform | 🟢 BAS | Post-infra |
| D-L1B-ENV-2 | Supprimer variables redondantes | 🟢 BAS | Post-infra |
| D-L1B-ENV-3 | Renommer `LABEL_STUDIO_HOST` | 🟢 BAS | Post-infra |
| D-L1B-ENV-4 | Documenter variables non-DMS héritées | 🟢 BAS | Post-infra |
| D-INFRA-ENV-1 | Upgrade client psql 16 → 17 (alignement serveur) | 🟡 MOYEN | Post-infra |
| D-INFRA-ENV-2 | Config code page UTF-8 PowerShell | 🟢 BAS | Post-infra |
| D-L1C-LATENCY | Instrumentation latence précise requêtes DB | 🟡 MOYEN | Phase 2+ |
| **D-L1D-BIS-TUNNEL** | Résoudre voie L2+ (tunnel 45+ min impossible) | 🔴 **BLOQUANT** | **Avant Phase 2** |

### Findings Phase 1

1. **Backend `/health` lent** (L1-A) : p95 1.09s, dépasse cible 500ms pilote
2. **Configuration env vars saine** (L1-B) : aucune divergence critique détectée
3. **Voie `railway connect postgres` validée** (L1-C) : TLS actif, mesures SQL OK avec psql installé
4. **Voie `railway run` non viable** (L1-D auxiliaire) : DNS resolution fail systématique depuis agent
5. **Timeout Railway 15 min** (L1-D-bis) : Sessions `railway connect postgres` fermées par serveur après ~15 min

---

## 5. Blocage architectural identifié + décision CTO principal

### Constat Phase 1

**Aucune des 2 voies L2 testées (fidelity ladder niveau 3) ne tient 45 minutes** :
- `railway run` + Python/psycopg → échec DNS resolution (0% succès)
- `railway connect postgres` + psql interactif → rupture session ~15 min

### Décision CTO principal tracée — Option C retenue

**Option C — Worker Railway interne** est actée comme direction d'architecture pour résoudre le blocage L2+.

**Principe** : Déployer un compute Python dans le réseau Railway (même projet que PostgreSQL), éliminant la dépendance aux tunnels CLI externes et aux timeouts de sessions interactives. Le worker accède à `DATABASE_URL` nativement sans proxy `maglev.proxy.rlwy.net` depuis l'extérieur.

**Décision opposable** : Avant toute ouverture opérationnelle de la suite du chantier infra au-delà de la clôture Phase 1, un chantier worker Railway dédié sera ouvert par mandat séparé, borné et opposable.

---

## 6. Conclusion de phase

### Phase 1 — Statut

🟢 **CLOSE** — Phase 1 I-DEBT-2 clôturée sur diagnostic opposable complet.

**Livrables produits** :
- L1-A : Baseline `/health` backend (SLO-1 rouge mesuré)
- L1-B : Delta env vars (4 dettes mineures tracées)
- L1-B-bis : Registre dette env vars
- L1-C : Validation tunnel Railway CLI (voie psql validée)
- L1-D : Test `railway run` (non recevable, diagnostic auxiliaire)
- L1-D-bis : Test stabilité psql 45 min (SLO-3 FAIL recevable)
- L1-E (ce document) : Synthèse Phase 1

**Verdicts opposables** :
- SLO-1 = 🔴 ROUGE (p95 `/health` = 1.09s)
- SLO-3 = 🔴 FAIL (rupture tunnel 15 min, cible 45 min)

### Phase 2 — Statut

🔴 **INTERDITE** — Phase 2 reste bloquée tant que le chantier worker Railway (Option C) n'est pas ouvert et validé.

**Blocage architectural** : Absence de voie L2+ stable 45+ min empêche tout benchmark E4-quater ou diagnostic I-DEBT-1 backend long-running.

### Prochaine étape

**Ouverture chantier worker Railway** par mandat séparé, borné et opposable, avant toute ouverture opérationnelle de la suite du chantier infra au-delà de la clôture Phase 1.

**Référence décision** : Pré-arbitrage CTO principal C3 confirmé 2026-04-22, intégré mandat L1-E §A formulation opposable gravée.

---

**Fin L1-E. Phase 1 close. Chantier worker requis avant Phase 2.**
