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
| `MAX_TEXT_CHARS` | Troncature du texte envoyé au LLM (défaut 200000) |
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

## Dépôt corpus m12-v2 (webhook → stockage durable)

Après `ANNOTATION_CREATED` / `ANNOTATION_UPDATED`, le backend peut construire une ligne m12-v2 et l’écrire dans un sink (fichier local, S3-compatible, ou noop). Sur Railway sans volume, privilégier **S3** (ex. R2, bucket S3).

| Variable | Description |
| --- | --- |
| `CORPUS_WEBHOOK_ENABLED` | `1` / `true` / `yes` / `on` : activer le traitement asynchrone après `POST /webhook`. |
| `CORPUS_WEBHOOK_ACTIONS` | Liste séparée par virgules (défaut : `ANNOTATION_CREATED,ANNOTATION_UPDATED`). |
| `CORPUS_WEBHOOK_STATUS_FILTER` | Si non vide : n’écrire que lorsque le statut LS (`annotation_status`) est égal à cette valeur (ex. `annotated_validated`). |
| `M12_EXPORT_ENFORCE_VALIDATED_QA` | Aligné sur le script d’export : si `annotated_validated`, marquer erreurs si QA / finances / evidence échouent (défaut : activé). |
| `M12_EXPORT_REQUIRE_LS_ATTESTATIONS` | Exiger attestations XML quand validé (défaut : désactivé). |
| `LABEL_STUDIO_URL` | URL de l’instance LS (re-fetch tâche/annotation si le webhook est incomplet). |
| `LABEL_STUDIO_API_KEY` | Token API LS (`Authorization: Token …`). |
| `LS_URL` / `LS_API_KEY` | **Repli** accepté si les variables `LABEL_STUDIO_*` ne sont pas définies (même valeur). |
| `LABEL_STUDIO_PROJECT_ID` | Fallback si le webhook ne fournit pas `project.id` (ni sur la tâche). |

### Sink

| Variable | Description |
| --- | --- |
| `CORPUS_SINK` | `noop` (défaut), `file`, ou `s3`. |
| `CORPUS_FILE_PATH` | Chemin JSONL si `CORPUS_SINK=file` (données perdues sans volume persistant). |
| `S3_BUCKET` | Bucket si `CORPUS_SINK=s3`. |
| `S3_ENDPOINT` | URL du endpoint S3-compatible (ex. R2) ; vide pour AWS par défaut. |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | Ou `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. |
| `S3_REGION` | Région explicite (ex. `eu-west-1` pour **AWS S3**). Si vide et **`S3_ENDPOINT`** est défini (R2, MinIO), le client utilise `auto`. Si endpoint vide (AWS natif), la région n’est pas forcée — utiliser `AWS_DEFAULT_REGION` ou config boto si besoin. |
| `S3_ADDRESSING_STYLE` | Optionnel : `path` ou `virtual` pour forcer le style d’URL S3 ; laisser vide pour R2 (défaut boto3). |
| `S3_CORPUS_PREFIX` | Préfixe des clés objet (défaut : `m12-v2`). Idempotence : une clé par `project_id/task_id/annotation_id/content_hash`. |

**Dépannage R2 / S3** : si les logs montrent `SignatureDoesNotMatch` sur `PutObject` :

1. Vérifier que les clés sont des **jetons API R2** (droits objet) ou paires IAM **AWS**, sans espace ni retour ligne en tête/fin (copier-coller Railway).
2. **`S3_ENDPOINT`** = URL exacte du type `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` (sans slash final).
3. Ne pas mélanger une **access key** d’un compte et un **secret** d’un autre ; régénérer les clés dans le dashboard si besoin.
4. Par défaut le client **ne force pas** `path`-style (aligné doc R2). Si besoin (MinIO, etc.) : `S3_ADDRESSING_STYLE=path` ou `virtual`.

### Sécurité webhook

| Variable | Description |
| --- | --- |
| `WEBHOOK_CORPUS_SECRET` | Si défini, le header HTTP `X-Webhook-Secret` doit correspondre exactement ; sinon `401` sur `POST /webhook`. |

## Développement local

| Variable | Description |
| --- | --- |
| `ALLOW_WEAK_PSEUDONYMIZATION` | `1` uniquement en dev si `PSEUDONYM_SALT` absent (non conforme prod). |
