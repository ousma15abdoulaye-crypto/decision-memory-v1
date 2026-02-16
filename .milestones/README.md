# Milestones — Gates CI (V3.3.2)

Les gates (coverage, invariants) ne deviennent **bloquantes** que lorsque le milestone correspondant est marqué DONE.

## Marquer un milestone DONE

Créer un fichier vide (ou avec contenu optionnel) :

```
.milestones/<ID>.done
```

Exemple : `.milestones/M-TESTS.done` active la gate de coverage.

## IDs et gates

| Fichier `.done` | Effet |
|-----------------|--------|
| **M-TESTS.done** | Gate coverage active dans `ci-main.yml` : `pytest --cov-fail-under=40`. Sans ce fichier : `--cov-fail-under=0` (reporting seulement). |
| **M-CI-INVARIANTS.done** | Workflow `ci-invariants.yml` devient bloquant : exige `tests/invariants/` et lance `pytest tests/invariants -v`. Sans ce fichier : mode "report" uniquement (exit 0). |

## Règle

Ne pas créer un `.done` tant que le travail du milestone n’est pas terminé (tests invariants écrits, coverage ≥ 40 % atteint, etc.).
