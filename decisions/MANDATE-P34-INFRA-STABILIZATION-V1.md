# DMS — Mandat de phase : P3.4-INFRA-STABILIZATION

**Référence** : DMS-MANDATE-P34-INFRA-STABILIZATION-V1  
**Date d'ouverture** : 2026-04-21  
**Auteur** : CTO Senior DMS  
**Validation pending** : CTO principal DMS  
**Statut** : OUVERTE (exécution post-merge PR E4-session-close)

---

## Contexte

Session E4/E4-bis/E4-ter (2026-04-20 → 2026-04-21) a produit triple verdict NON CONCLUANT infrastructure. Trois dettes révélées : I-DEBT-1, 2, 3 (voir `decisions/P34_E4BIS_RAPPORT_TOURS_3_4_5.md`).

Le pipeline P3.4 reste non démontré opérationnel sur réel tant que l'infra pilote n'est pas stabilisée. Cette phase devient chemin critique avant P3.4B, P3.4C, P3.5.

---

## Périmètre

### I-DEBT-1 : Backend annotation extraction stable

**Objectif** : extraction d'un document < 30s en p95.

**Diagnostic requis** :
- Cold start Railway (mesurer temps de warm-up)
- Charge OCR (mesurer latence Mistral OCR sur docs SCI typiques)
- Rate limit Mistral API (vérifier quota + 429s)
- Dimensionnement Railway (CPU/RAM du service annotation-backend)

**Fix attendus** (ordre de priorité) :
1. Warm-up / keep-alive si cold start confirmé
2. Upgrade plan Railway si dimensionnement insuffisant
3. Stratégie retry + backoff sur rate limit Mistral
4. Monitoring latence p95 + alerting SLO

### I-DEBT-2 : Connexion DB stable depuis dev

**Objectif** : 0 `getaddrinfo failed` sur session dev de 30 minutes.

**Options à évaluer** :
- **Option L1** : PostgreSQL local Docker mirror synchronisé Railway
- **Option L2** : Tunnel Railway CLI (`railway connect postgres`)
- **Option L3** : VPN / connexion privée Railway (plan payant)

**Critère de choix** : pragmatisme + coût + fidélité au réel.

### I-DEBT-3 : Documentation ops Railway exhaustive

**Livrables** :
- `services/annotation-backend/ENVIRONMENT.md` exhaustif (toutes env vars, toutes dépendances Mistral / DB / S3 / Langfuse)
- `docs/ops/RAILWAY_RUNBOOK.md` (déploiement, restart, monitoring, diagnostic)
- SLO formalisés :
  - /health p95 < 500ms
  - Extraction p95 < 30s
  - Uptime > 99%

---

## Exclusions (ce que cette phase NE fait PAS)

- ❌ Industrialisation annotation-backend N1/N2/N3 (reste horizon P6–P7, gouvernée par DMS-ARCH-PROPOSAL-ANNOTATION-BACKEND-INDUSTRIALIZATION)
- ❌ Modification du code métier pipeline P3.4 (reste gelé §8)
- ❌ Relancement E4-quater (attendu en clôture de phase)

---

## Critère de clôture

E4-quater exécuté avec succès sur CASE-28b05d85 :
- 2 runs idempotence V3 complets
- Matrice produite avec invariants I1–I6 respectés
- Anomalies ⊆ {A1–A6} ou documentées hors liste
- SLO infra respectés sur durée session benchmark

---

## Horizon

Pas d'horizon contraint — **qualité > vitesse**. La phase clôt quand les 3 dettes sont résolues, pas quand un calendrier l'exige.

Priorité absolue avant reprise P3.4B / P3.4C / P3.5.

---

## Traçabilité

- Déclencheur : DMS-ARBITRAGE-CTO-SENIOR-TRIPLE-NONCONCLUANT-STRATEGY-V1
- Rapport source : decisions/P34_E4BIS_RAPPORT_TOURS_3_4_5.md
- Doctrines applicables : G1 (fix ops ≠ industrialisation), G14 (calibration), G17 (trace honnête), G19 (preflight infra), G20 (signal systémique)
