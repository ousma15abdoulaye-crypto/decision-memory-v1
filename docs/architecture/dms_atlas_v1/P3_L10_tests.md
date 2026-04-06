# P3 — Livrable 10 : Tests et qualité

## 10.1 Inventaire

| Métrique | Valeur (mesure 2026-04-06) |
|----------|----------------------------|
| Fichiers `tests/**/*.py` | 267 |
| Lignes de code tests | ~35 160 |
| Fonctions `test_*` | **827** (comptage regex `^def test_`) |
| Framework | **pytest** |

**Tests d’intégration** : répertoire [`tests/integration/`](../../tests/integration/), [`tests/db_integrity/`](../../tests/db_integrity/).

**Tests E2E** : scripts sous [`scripts/`](../../scripts/) (ex. `test_extraction_e2e.py`) — classification **scripts**, pas `tests/` standard.

## 10.2 Couverture

- CI : [`ci-main.yml`](../../.github/workflows/ci-main.yml) exécute  
  `pytest tests/ --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=${fail_under}`.
- **Seuil** : si le fichier [`.milestones/M-TESTS.done`](../../.milestones/M-TESTS.done) existe → `fail_under=65` ; sinon **0**.

**Couverture par module** : voir rapport `coverage.xml` / Codecov en CI — **non recopié** dans ce dossier.

## 10.3 Qualité statique

- **Ruff** + **Black** sur `src`, `tests` (et `services/` selon mandats) — mêmes commandes que CI.

## 10.4 Tests de performance / charge

**NON** trouvés comme suite dédiée dans `tests/` — pas de benchmark utilisateur simultané versionné ici.

## 10.5 Mocking

- `TESTING=true` désactive certains rate limits ([`ratelimit.py`](../../src/ratelimit.py)).
- Conftest multiples par domaine — voir `tests/**/conftest.py`.
