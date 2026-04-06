# Gate de couverture pytest (`--cov-fail-under`)

## Comportement CI (`ci-main.yml`)

Le job **lint-and-test** calcule le seuil minimal ainsi :

- Si le fichier **`.milestones/M-TESTS.done`** est présent à la racine du dépôt → `fail_under=65` (couverture **bloquante** sur `src/`).
- Sinon → `fail_under=0` (les tests doivent passer ; la couverture n’est pas un échec CI).

Référence : étape **Resolve coverage gate** dans [`.github/workflows/ci-main.yml`](../../.github/workflows/ci-main.yml).

## État actuel

Le dépôt inclut **`.milestones/M-TESTS.done`** : sur `main`, la CI applique donc **`--cov-fail-under=65`** pour `pytest tests/ --cov=src`.

## Recommandation produit

Pour les phases « enterprise », conserver ce fichier et traiter toute régression de couverture sous le seuil comme **échec de merge**, sauf décision CTO documentée (retrait temporaire du fichier = assouplissement explicite).
