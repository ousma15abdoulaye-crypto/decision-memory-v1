# Setup développeur — DMS

## Frontend V5.1 (`frontend-v51`)

### Prérequis

- Node 20+ (aligné CI)
- Backend API optionnel pour les pages authentifiées ; certaines pages peuvent être testées avec mocks (E2E).

### Commandes courantes

```bash
cd frontend-v51
npm ci
npm run build
npm run lint
```

### Playwright (E2E)

Les E2E sont **obligatoires avant merge** (local ou CI GitHub Actions — job **`frontend_v51_e2e`** / étape *Test 17 — Playwright E2E*, voir [`.github/workflows/dms_invariants_v51.yml`](../../.github/workflows/dms_invariants_v51.yml)).

```bash
cd frontend-v51
npx playwright install --with-deps chromium
npm run test:e2e
```

#### Erreur TLS (*unable to get local issuer certificate*) — proxy d’entreprise

Sur un poste derrière inspection TLS, le téléchargement des navigateurs Playwright peut échouer.

**Option A (contournement strictement local, jamais en prod)** — à n’utiliser qu’en dernier recours et sous responsabilité locale :

```bash
# PowerShell
$env:NODE_TLS_REJECT_UNAUTHORIZED="0"; npx playwright install --with-deps chromium
npm run test:e2e
```

```bash
# bash
NODE_TLS_REJECT_UNAUTHORIZED=0 npx playwright install --with-deps chromium
npm run test:e2e
```

**Option B** — laisser **CI GitHub** exécuter `npm run test:e2e` après `npm run build` (environnement sans proxy TLS cassé) et ne merger qu’avec le job vert.

**Option C** — configurer le proxy / certificat racine d’entreprise dans Node (variable `NODE_EXTRA_CA_CERTS`, etc.) selon la politique IT.

### Next.js 16 — avertissement *middleware → proxy*

Le build peut afficher un avertissement sur la convention `middleware`. Suivi : dette documentée dans [`FRONTEND_V51_NL_TECH_DEBT.md`](./FRONTEND_V51_NL_TECH_DEBT.md) (migration vers la convention *proxy* Next.js 16).
