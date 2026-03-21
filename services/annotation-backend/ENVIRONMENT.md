# Variables d’environnement — DMS Annotation Backend

Déploiement (Railway, Docker, etc.) : aligner avec [`docs/m12/M12_INFRA_SMOKE.md`](../../docs/m12/M12_INFRA_SMOKE.md).

## Railway (build Docker monorepo)

Le `Dockerfile` copie `services/annotation-backend/*` **et** `src/annotation` depuis la **racine du dépôt**. Le contexte Docker doit donc être le repo entier.

1. Service → **Settings** → **Root Directory** : laisser **vide** ou `.` (racine du repo), **pas** `services/annotation-backend`.
2. **Dockerfile Path** : `services/annotation-backend/Dockerfile` (déjà indiqué dans `railway.json` si la config code est reliée depuis ce fichier).
3. Fichier config Railway : le [guide monorepo](https://docs.railway.com/guides/monorepo) précise que le chemin du `railway.json` ne suit pas automatiquement le root — pointer vers `services/annotation-backend/railway.json` si besoin.

Si le root reste `services/annotation-backend` seul, l’erreur `"/src": not found` (ou équivalent) est attendue : Docker ne peut pas lire le dossier parent.

## Obligatoires (prod)

| Variable | Description |
| --- | --- |
| `MISTRAL_API_KEY` | Appel API Mistral |
| `PSEUDONYM_SALT` | Sel HMAC pour pseudonymisation phone/email en sortie LS |

## Recommandées

| Variable | Description |
| --- | --- |
| `MISTRAL_MODEL` | Défaut : `mistral-small-latest` |
| `CORS_ORIGINS` | URL publique Label Studio (séparateur virgule) ; éviter `*` en prod |
| `MAX_TEXT_CHARS` | Troncature du texte envoyé au LLM (défaut 80000) |
| `MIN_LLM_CONTEXT_CHARS` | Seuil minimum pour appeler Mistral |
| `MIN_PREDICT_TEXT_CHARS` | Seuil côté `/predict` avant refus « texte trop court » |

## Review financier (ARCH-04)

| Variable | Description |
| --- | --- |
| `FINANCIAL_REVIEW_THRESHOLD_XOF` | Seuil « montant élevé » (prudence locale pipeline) pour `taxonomy_core=offer_financial`. Défaut : `10000000`. |

## Mode strict pré-annotation

| Variable | Description |
| --- | --- |
| `STRICT_PREDICT` | Si `1` / `true` / `yes` / `on` : pas de JSON de pré-annotation si échec schéma Pydantic, réconciliation financière (`annotation_qa`) ou contrôle evidence vs texte. `GET /health` expose `strict_predict`. |

**Choix prod** : laisser désactivé tant que les annotateurs ont besoin d’un brouillon Mistral à corriger ; activer pour les dossiers où seule une extraction entièrement valide est acceptée.

## Développement local

| Variable | Description |
| --- | --- |
| `ALLOW_WEAK_PSEUDONYMIZATION` | `1` uniquement en dev si `PSEUDONYM_SALT` absent (non conforme prod). |
