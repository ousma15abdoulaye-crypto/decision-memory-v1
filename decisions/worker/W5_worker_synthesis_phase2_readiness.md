# W5 — Synthèse sous-chantier Worker Railway & Readiness Phase 2

**Autorité** : CTO principal DMS (décision gate W3-bis 2026-04-23 + W4 validé)  
**Auteur** : Agent Claude Code (mandat DMS-MANDAT-W5-WORKER-SYNTHESIS-V1)  
**Date** : 2026-04-23  
**Statut** : ✅ CLÔTURE SOUS-CHANTIER — Phase 2 ouvrable sous mandat dédié

---

## 1. Rappel ADR Option C et mandat chantier worker

### ADR Option C — Worker Railway interne

**Référence** : ADR-P34-INFRA-OPTION-C-WORKER-RAILWAY-V1 (SIGNÉ / APPROVED)  
**Document** : `decisions/adr/ADR_P34_INFRA_OPTION_C_WORKER_RAILWAY_V1.md`

**Décision architecturale** : Déployer un compute Python (FastAPI) dans le réseau Railway (même projet PostgreSQL DMS) pour accéder à `DATABASE_URL` nativement via réseau interne `postgres.railway.internal`, contournant les limitations Layer 2 (tunnels Railway CLI externes).

**Contexte déblocage** : Phase 1 I-DEBT-2 (SLO-3 FAIL) a révélé qu'aucune voie L2 ne tient 45+ min :
- L1-D : `railway run` DNS failure 100%
- L1-D-bis : `railway connect postgres` déconnexions ~15 min

Option C adoptée pour résoudre le blocage infra empêchant sessions annotation longues et benchmark backend E4.

### Mandat sous-chantier worker

**Chantier** : P3.4-INFRA-WORKER-DEPLOYMENT  
**Chantier parent** : P3.4-INFRA-STABILIZATION  
**Branche** : `chore/p3-4-infra-stabilization`

**Fragments prévus** :
1. **W1** — Spec technique worker Railway
2. **W2** — POC déploiement et validation endpoints
3. **W3** — Test stabilité longue durée (initial)
4. **W3-bis** — Test stabilité corrigé (run W3 INCONCLUSIF)
5. **W5** — Synthèse et clôture sous-chantier (ce document)

---

## 2. Synthèse fragments W1 → W4

### W1 — Spec technique worker Railway

**Commit référence** : `63be682d` — docs(infra-worker): W1 worker Railway spec  
**Document** : `decisions/worker/W1_worker_railway_spec.md`  
**Statut** : ✅ RECEVABLE

**Livrable** : Spécification technique opposable du worker Railway DMS. Stack retenue : Python 3.11 + FastAPI + uvicorn + psycopg[binary] v3.x (async PostgreSQL). Architecture 3 endpoints read-only (`/health`, `/db/ping`, `/db/info`) avec authentification bearer token. Déploiement Railway via Nixpacks, service link PostgreSQL pour injection `DATABASE_URL` automatique. Spec alignée contraintes D-INFRA-5 (cohérence stack annotation-backend) et exigences sécurité (token rotation, logs structurés JSON).

### W2 — POC déploiement et validation endpoints

**Commits référence** : `cf7c8a11`, `0135397b`, `8bda421f`  
**Document** : `decisions/worker/W2_worker_railway_poc.md`  
**Statut** : ✅ POC VALIDÉ

**Livrable** : Worker Railway déployé sur service `dms-db-worker` (URL publique `https://dms-db-worker-production.up.railway.app`). Validation opérationnelle : 3 endpoints fonctionnels avec auth bearer, connectivité PostgreSQL interne validée (latence DB p95=54ms < 100ms cible), healthcheck Railway opérationnel. Issues résolues : root directory Railway, token avec chevrons, healthcheck public `/healthz` séparé de `/health` authentifié. POC démontre viabilité architecture Option C, prêt pour test stabilité longue durée W3.

### W3 — Test stabilité initial

**Commit référence** : `79981a6f` — docs(worker): W3 stability test INCONCLUSIF  
**Document** : `decisions/worker/W3_worker_railway_stability_45min.md`  
**Statut** : ⚠️ INCONCLUSIF / NON RECEVABLE

**Livrable** : Test stabilité 50 min run 1 échoué avec gap 12 minutes inexpliqué (suspension système Windows probable), latences non mesurées (erreur parsing `bc`), run incomplet 66/100 pings. Aucune donnée exploitable pour verdict sur stabilité longue durée. Observations partielles : 66/66 HTTP 200, aucun timeout DB visible, mais critère continuité invalidé par gap. W3-bis requis avec harness corrigé.

### W3-bis — Test stabilité corrigé

**Commit référence** : `6e7fe546` — fix(W3-bis): reclassify verdict as PASS PARTIEL  
**Document** : `decisions/worker/W3_bis_worker_railway_stability_50min.md`  
**Statut** : ⚠️ PASS PARTIEL

**Livrable** : Test stabilité 50 min run 2 avec harness corrigé (parsing latence robuste awk, heartbeat, validation gaps). Résultats : 83/83 pings HTTP 200 (100% succès observé), session continue 50 min sans déconnexion, aucun timeout DB, aucun gap > 60s, latence DB interne ~52ms (normale). Protocole incomplet 83/100 pings dû à latence réseau local Windows → Railway (artifact non représentatif du worker). Verdict CTO principal : PASS PARTIEL suffisant pour lever blocage infra, stabilité fortement corroborée, dette résiduelle protocole incomplet actée non bloquante.

### W4 — Runbook opérationnel

**Commit référence** : `0b4eb186` — docs(worker): W4 runbook opérationnel  
**Document** : `decisions/worker/W4_worker_runbook.md`  
**Statut** : ✅ VALIDÉ (681 lignes, conservé en l'état)

**Livrable** : Runbook opérationnel opposable du worker Railway `dms-db-worker`. 7 sections : identité service (URL, commit code référence, variables env), procédures démarrage/arrêt/redéploiement, configuration variables Railway, surveillance santé (endpoints, logs, seuils), diagnostic 5 symptômes types (DB unreachable, latence dégradée, service DOWN, 401, redéploiement échoué), dette résiduelle W3-bis tracée, contacts escalade. Document production permettant exploitation worker sans reconstituer contexte.

---

## 3. Verdict opposable sous-chantier

### Verdict général

**Option C (worker Railway interne) = ARCHITECTURALEMENT VALIDÉE**

Le sous-chantier P3.4-INFRA-WORKER-DEPLOYMENT a démontré la viabilité de l'architecture Option C pour résoudre le blocage infra Phase 1 I-DEBT-2. Worker Railway opérationnel, déployé, documenté, stable sur 50 min continues sans déconnexion.

**Blocage infra Phase 1 LEVÉ** sur décision CTO principal DMS 2026-04-23 (décision gate W3-bis).

### Trois points opposables W3-bis à graver

Les trois points suivants sont **opposables** et doivent être respectés dans toute référence future à la décision gate W3-bis :

**(a) W3-bis = PASS PARTIEL suffisant pour déblocage**

Le run W3-bis a validé la stabilité observée du worker Railway sur 50 minutes continues avec 83/83 réponses HTTP 200, aucun gap > 60s et aucun timeout DB. Le protocole nominal n'ayant pas été complété jusqu'à 100 pings (83/100), ce run ne peut être classé en PASS plein au sens strict, mais est jugé suffisant pour lever le blocage infra.

**(b) Dette résiduelle = protocole incomplet 83/100 pings, non bloquante**

Le caractère incomplet du protocole W3-bis (83/100 pings exécutés au lieu de 100) est conservé comme **dette de preuve résiduelle, non bloquante** pour production. La stabilité du worker est fortement corroborée par les 50 minutes continues sans déconnexion ni erreur DB observées. Cette dette n'empêche pas l'usage production du worker.

**(c) Futur test strict sera relancé uniquement en cas de symptôme nouveau ou d'exigence formelle spécifique**

Aucun W3-ter n'est requis immédiatement. Un test de complétude strict (100/100 pings) sera considéré uniquement si : (1) un symptôme nouveau apparaît en production (déconnexions récurrentes, timeouts DB non anticipés), ou (2) une exigence formelle est émise (audit, compliance, gate SI). En l'absence de ces conditions, le PASS PARTIEL W3-bis reste le verdict opposable.

---

## 4. Findings transverses et actifs acquis

### Findings transverses

**Latence p95 externe vs. latence interne worker**

Les tests W3 et W3-bis ont révélé un écart significatif entre :
- **Latence mesurée côté client externe** (Windows → Railway HTTPS) : 1.2s–10s (W3-bis)
- **Latence mesurée côté worker interne** (worker → PostgreSQL Railway) : ~52ms (endpoint `/db/ping`)

**Interprétation** : Les latences élevées mesurées côté client externe sont un **artifact du chemin réseau local de test** (Windows Git Bash → Internet → Railway HTTPS), **non représentatives** de la performance du worker Railway lui-même. Le worker accède à PostgreSQL en ~52ms via réseau interne Railway, performance normale et conforme cible p95 < 100ms.

**Impact** : Aucune dégradation worker identifiée. Les mesures futures de performance backend doivent être effectuées **depuis l'intérieur du réseau Railway** (via worker ou autre compute Railway) pour obtenir des mesures représentatives, pas depuis clients externes.

### Actifs acquis

**1. Worker Railway opérationnel**

Service `dms-db-worker` déployé et opérationnel sur Railway, accès PostgreSQL interne stable, 3 endpoints read-only (`/health`, `/db/ping`, `/db/info`) avec authentification bearer token. Architecture validée pour sessions longues 45+ min.

**2. Runbook opérationnel opposable**

Document `decisions/worker/W4_worker_runbook.md` permet exploitation, surveillance, diagnostic et redéploiement worker sans reconstituer contexte. Procédures exactes, 5 symptômes types couverts, contacts escalade tracés.

**3. Patterns déploiement Railway réutilisables**

- Configuration multi-services monorepo via `railway.toml` (root directory)
- Service link PostgreSQL pour injection `DATABASE_URL` automatique
- Healthcheck public séparé (`/healthz`) vs. endpoints métier authentifiés
- Rotation secrets Railway via Variables (procédure documentée W4)

**4. Apprentissages test stabilité**

- Harness test longue durée : parsing robuste (awk), heartbeat horodaté, validation gaps automatique
- Preflight environnement : désactivation veille Windows obligatoire pour tests 45+ min
- Logs Railway CLI : commande `--follow` non supportée toutes versions, fallback dashboard

### Dettes identifiées

**Dette de preuve résiduelle W3-bis** : Protocole incomplet 83/100 pings (détaillé §3, non bloquante).

**Pas d'autre dette technique majeure identifiée** pendant fragments W1-W4.

---

## 5. Transition vers Phase 2 I-DEBT-1

### Prérequis infra désormais réunis

**Phase 2 I-DEBT-1** : Backend extraction 120s sous charge OCR (SLO-2 ROUGE : p95 extraction 1 document > 30s)

Les prérequis infra pour investigation Phase 2 sont **désormais réunis** :
- ✅ Worker Railway opérationnel avec accès PostgreSQL interne stable
- ✅ Capacité mesure depuis réseau interne Railway (via worker endpoints)
- ✅ Blocage infra Phase 1 levé (sessions longues 45+ min validées)

### Pré-requis Phase 2 à acter dans mandat dédié

Les éléments suivants devront être adressés dans le **mandat Phase 2 dédié** (hors scope W5) :

**1. Utilisation worker pour requêtes DB benchmark E4-quater**

Le worker `dms-db-worker` pourra être utilisé comme point de mesure depuis l'intérieur Railway pour caractériser la charge backend annotation sous charge OCR. Endpoints à définir (lecture documents, extraction metadata) selon protocole E4-quater révisé.

**2. Protocole mesure backend via worker**

Définir protocole mesure extraction backend utilisant worker Railway :
- Charge OCR simulée ou réelle (volume documents, fréquence requêtes)
- Métriques capturées (latence p50/p95/max extraction, taux échec, charge DB)
- Critères acceptation (SLO-2 cible : p95 extraction < 30s)

**3. SLO-2 cible à valider**

SLO-2 actuel : extraction 1 document p95 < 30s. À confronter au finding L1-A : endpoint `/health` annotation-backend déjà 1.09s au repos (marge étroite 30s - 1.09s = 28.91s disponible pour extraction métier).

Validation SLO-2 cible à effectuer en Phase 2 selon charge réelle mesurée.

### Recommandation CTO Senior

**Phase 2 I-DEBT-1 ouvrable par mandat dédié** une fois sous-chantier worker clos (W5 validé).

Phase 2 ne s'ouvre **pas** dans ce livrable W5. Elle nécessite :
- Mandat Phase 2 dédié émis par CTO principal
- Cadrage périmètre (backend annotation-backend code métier) vs. STOP-INFRA-1
- Protocole E4-quater révisé ou nouveau benchmark défini
- Validation SLO-2 cible selon contraintes réelles

**Points de vigilance Phase 2** :
- Backend annotation-backend actif production → modifications code métier à border finement (STOP-INFRA-1)
- Utilisation worker Railway comme mesure interne (éviter artifact réseau externe)
- Findings L1-A `/health` 1.09s au repos → marge étroite pour atteindre p95 < 30s

---

## 6. Conclusion et interdits maintenus

### Clôture sous-chantier

**Sous-chantier P3.4-INFRA-WORKER-DEPLOYMENT = CLOS**

Les 5 fragments prévus (W1 → W5) ont été livrés et validés. Option C architecturalement validée, worker opérationnel, runbook opposable produit, blocage infra Phase 1 levé.

**Livrables produits** :
- W1 : Spec technique (commit `63be682d`)
- W2 : POC déploiement (commits `cf7c8a11`, `0135397b`, `8bda421f`)
- W3 : Test stabilité initial (commit `79981a6f`, INCONCLUSIF)
- W3-bis : Test stabilité corrigé (commit `6e7fe546`, PASS PARTIEL)
- W4 : Runbook opérationnel (commit `0b4eb186`)
- W5 : Synthèse et clôture (ce document)

### Phase 2 I-DEBT-1 : ouvrable, pas ouverte

**Phase 2 I-DEBT-1** (backend extraction 120s sous charge OCR) est **ouvrable** sous mandat dédié CTO principal. Elle n'est **pas ouverte** dans ce livrable W5.

Prérequis infra réunis, mais Phase 2 nécessite cadrage propre, protocole mesure défini, validation SLO-2 cible, et périmètre backend annotation-backend à border (STOP-INFRA-1).

### Interdits maintenus

Les interdits suivants restent **actifs** jusqu'à levée explicite CTO principal :

**STOP-INFRA-1** : Pas de modification code métier pipeline annotation pour contourner problème infra

Aucune modification des extracteurs spécialisés, router, validator, ou orchestration backend annotation-backend pour compenser lenteur extraction sous charge. Phase 2 doit caractériser le problème, pas le contourner par code métier.

**STOP-INFRA-3** : Pas de relance benchmark E4-quater sans mandat explicite

Le benchmark E4 post-merge PR #430 Draft reste **CLOS INCONCLUSIVE** (commit `10ee7139`). Aucune relance E4-quater sans mandat Phase 2 dédié définissant protocole révisé, charge OCR, et utilisation worker Railway pour mesure interne.

**PR #430 Draft** : Non mergée jusqu'à benchmark E4-quater ACCEPTÉ

La pull request #430 (Draft) reste **non mergée** jusqu'à validation formelle que les modifications n'impactent pas performance backend sous charge OCR. Phase 2 pourrait utiliser branche PR #430 comme baseline comparative si pertinent.

### Chantiers latents reportés

Les chantiers latents CL-1 à CL-6 identifiés en L1-E restent **reportés** hors Phase 2 immédiate (décision CTO principal à acter selon roadmap).

---

## Changelog

| Date       | Version | Auteur    | Changement                                |
|------------|---------|-----------|-------------------------------------------|
| 2026-04-23 | 1.0.0   | Agent W5  | Synthèse clôture sous-chantier worker    |

---

**Statut final** : ✅ SOUS-CHANTIER P3.4-INFRA-WORKER-DEPLOYMENT CLOS — Phase 2 I-DEBT-1 ouvrable sous mandat dédié  
**Dernière révision** : 2026-04-23  
**Prochaine étape** : Émission mandat Phase 2 I-DEBT-1 par CTO principal (si autorisée)
