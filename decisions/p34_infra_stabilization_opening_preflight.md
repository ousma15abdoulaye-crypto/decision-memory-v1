# DMS — Preflight P3.4-INFRA-STABILIZATION (Partiel)

**Référence** : DMS-PREFLIGHT-INFRA-STAB-PARTIAL-V1
**Date** : 2026-04-21
**Auteur** : Agent d'exécution DMS (reprise session)
**Statut livrable** : PARTIEL — qualitatif livré, quantitatif déféré Phase 1
**Mandat source** : DMS-MANDAT-REPRISE-AGENT-PREFLIGHT-INFRA-V1

## Note méthodologique

Ce preflight est volontairement partiel. Il consolide les données
qualitatives disponibles à la clôture de la session précédente et
identifie explicitement les mesures quantitatives à produire en
Phase 1 sous mandat fractionné. La doctrine G33 (production
incrémentale > exhaustivité théorique) guide cette approche.

## Bloc 1 — Topologie réelle (qualitatif)

### Sources consultées
- `services/annotation-backend/ENVIRONMENT.md` (22 KB, 209 lignes,
  exhaustif)
- `services/annotation-backend/backend.py` (100 premières lignes)
- `docs/ops/RAILWAY_MIGRATION_RUNBOOK.md`
- `docs/freeze/CONTEXT_ANCHOR.md`

### Services identifiés dans la topologie
- **Mistral API** : OCR + LLM (extraction documents)
- **PostgreSQL Railway** : DB principale DMS
- **Label Studio Railway** : annotation référentielle
- **S3 / R2** : via `CORPUS_SINK`, `S3_BUCKET` observé vide au
  démarrage (sink = noop jusqu'à correction)
- **Langfuse** : observability (clés vérifiées dans investigation
  antérieure)

### À produire Phase 1
- Diagramme ASCII complet du service mesh
- Vérification auth method par service
- SLO connus vs observés par service
- Comportement documenté en échec par service

## Bloc 2 — Symptômes prouvés session E4

### Séquence causale documentée
- **E4** (2026-04-20) : `ConnectError` annotation-backend
  (environnement agent local)
- **E4-bis** (2026-04-21) : `MISTRAL_API_KEY` absente côté backend
  Railway (fix ops appliqué)
- **E4-ter** (2026-04-21) : Timeout 120s extraction OCR +
  `DATABASE_URL` instable (`getaddrinfo failed` vers
  `maglev.proxy.rlwy.net`) + circuit breaker cascade

### Baseline observée ce tour (insuffisante)
- 1 `curl /health` backend Railway : HTTP 200,
  `mistral_configured: true`, backend UP

### À produire Phase 1
- Baseline `/health` p50/p95 sur 100 requêtes / 10 min
- Résolution DNS vers `maglev.proxy.rlwy.net`
- Latence TCP ping vers PostgreSQL Railway
- Tailles moyennes des 6 bundle_documents CASE-28b05d85

## Bloc 3 — I-DEBT-1 backend extraction

### Constat qualitatif
Timeouts 120s systématiques observés E4-ter sur extraction OCR,
même après configuration correcte de `MISTRAL_API_KEY`. Backend
répond `/health` mais ne tient pas la charge d'extraction réelle.

### Hypothèses en jeu (à départager Phase 2)
1. Cold start Railway (plan actuel à vérifier)
2. OCR lourd intrinsèquement long sur certains docs
3. Rate limit Mistral API (quota / 429 à vérifier)
4. Dimensionnement Railway insuffisant (CPU/RAM alloués)
5. Timeouts applicatifs mal calibrés
6. Dépendance aval lente mal observée

### À produire Phase 2
- Budget latence décomposé : OCR Mistral / LLM Mistral / DB insert /
  overhead HTTP / cold start
- Objectif SLO-2 : extraction 1 document p95 < 30s
- Instrumentation timing par sous-étape (middleware, logs
  structurés, Langfuse)

## Bloc 4 — I-DEBT-2 DB stable

### Constat qualitatif
`getaddrinfo failed` récurrent session E4-ter. Aucune connexion
DB stable démontrée sur durée >10 min depuis environnement agent.

### Options techniques (rappel mandat V1.1)
- **L1** : PostgreSQL local Docker mirror
- **L2** : Tunnel Railway CLI (décision CTO : préféré par défaut)
- **L3** : VPN / accès privé Railway (cible moyen terme)

### Recommandation L2+ (supervision active)
1. Tunnel Railway CLI dans `tmux`/`screen` auto-restart on failure
2. Health-check `SELECT 1` toutes les 30s + mesure latence
3. Fallback L1 documenté si tunnel down >2min pendant benchmark
4. Monitoring latence SELECT dans benchmark (alerte si p95 > 500ms)

### À produire Phase 1
- Implémentation L2+ avec supervision
- Test de stabilité 45 min continue
- Documentation procédure reproductible

## Bloc 5 — I-DEBT-3 documentation ops

### État existant observé
- `services/annotation-backend/ENVIRONMENT.md` existe (22 KB,
  exhaustif) — base solide
- `docs/ops/RAILWAY_MIGRATION_RUNBOOK.md` existe partiellement
- Pas de `RAILWAY_RUNBOOK.md` consolidé avec SLO

### À produire Phase 3
- Inventaire env vars delta (présentes / attendues / manquantes /
  superflues) via grep `os.getenv` + dump Railway
- `RAILWAY_RUNBOOK.md` consolidé : déploiement, restart, warm-up,
  diagnostic, lecture logs, procédures de reprise par mode d'échec
- SLO formalisés :
  - `/health` p95 < 500ms
  - Extraction p95 < 30s
  - Uptime > 99%

## Bloc 6 — Plan d'exécution (haut niveau)

| Phase | Objet | Critère sortie |
|---|---|---|
| Phase 0 | Preflight (ce livrable) | ✅ PARTIEL livré |
| Phase 1 | I-DEBT-2 DB stable + métriques Bloc 2 | SLO-3 tenu (session DB > 45 min sans rupture) |
| Phase 2 | I-DEBT-1 backend extraction | SLO-1 + SLO-2 tenus |
| Phase 3 | I-DEBT-3 runbook + SLO consolidés | Doc opposable externe |
| Phase 4 | Dry run E4-quater 1 document | Smoke test OK |
| Phase 5 | E4-quater complet (sous mandat explicite) | SLO-4 > 80% |

### Rollback par action
À produire dans mandats Phase 1, 2, 3 respectivement (non pertinent
Phase 0 diagnostic pur).

## Bloc 7 — Risques de fausse validation

### Risques identifiés
- **R1** : `/health 200` pris pour preuve de capacité opérationnelle
  (G19 — joignabilité ≠ capacité sous charge)
- **R2** : Local only validé comme preuve pilote (D-INFRA-4 — niveau
  1-2 fidelity ladder insuffisant)
- **R3** : Tunnel DB sans supervision donne illusion de stabilité
  (G27 — supervision active obligatoire)
- **R4** : Timeout simplement rallongé au lieu d'être diagnostiqué
  (D-INFRA-2 — observability before optimization)
- **R5** : Un fix Mistral qui masque un problème de dimensionnement
  Railway (diagnostic à remonter la chaîne §2.1 mandat V1.1)

### Garde-fous
Chaque SLO validé sur mesure effective, documentée, reproductible.
Jamais sur impression qualitative.

## Bloc 8 — Verdict

### Verdict opposable

**INSUFFICIENT DATA pour verdict READY complet**

Données qualitatives : **suffisantes** pour cadrer Phase 1.
Données quantitatives (baseline /health, budget latence
décomposé, inventaire env vars delta, test stabilité DB) :
**à produire Phase 1 sous mandat fractionné**.

### Recommandation CTO Senior

Procéder directement Phase 1 I-DEBT-2 avec mandat fractionné :
3 à 5 livrables courts (30 min max par livrable) au lieu d'un
méga-mandat. Premier livrable Phase 1 suggéré : **baseline
/health p50/p95 + test tunnel Railway CLI simple**.

### Doctrines gravées applicables

G19, G22, G27, G28, G32, G33 + D-INFRA-1 à 7.

---

**Fin du preflight partiel.**
**Prochaine étape attendue** : mandat CTO Senior Phase 1 fractionné.
