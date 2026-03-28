# Variables d’environnement — DMS Annotation Backend

Déploiement (Railway, Docker, etc.) : aligner avec [`docs/m12/M12_INFRA_SMOKE.md`](../../docs/m12/M12_INFRA_SMOKE.md).

## Railway (build Docker monorepo)

Le `Dockerfile` copie `services/annotation-backend/*` **et** `src/annotation` depuis la **racine du dépôt**. Le contexte Docker doit donc être le repo entier.

1. Service → **Settings** → **Root Directory** : laisser **vide** ou `.` (racine du repo), **pas** `services/annotation-backend`.
2. **Dockerfile Path** : `services/annotation-backend/Dockerfile` (déjà indiqué dans `railway.json` si la config code est reliée depuis ce fichier).
3. Fichier config Railway : le [guide monorepo](https://docs.railway.com/guides/monorepo) précise que le chemin du `railway.json` ne suit pas automatiquement le root — pointer vers `services/annotation-backend/railway.json` si besoin.

Si le root reste `services/annotation-backend` seul, l’erreur `"/src": not found` (ou équivalent) est attendue : Docker ne peut pas lire le dossier parent.

### `MISTRAL_API_KEY` vide dans les logs alors qu’elle est « définie » sur Railway

1. **Portée** : la variable doit être sur le **service** qui exécute ce Dockerfile (`annotation-backend`), pas seulement au niveau **Projet** si ce service n’hérite pas des variables partagées — dans Railway : **Service → Variables** pour ce service précis.
2. **Noms acceptés** : `MISTRAL_API_KEY` ou **`DMS_API_MISTRAL`** (Railway DMS). Repli : `MISTRAL_KEY` (`start.sh` le recopie vers `MISTRAL_API_KEY`).
3. **Valeur** : sans guillemets dans l’UI ; pas d’espace avant/après ; pas de retour ligne en trop (le `start.sh` normalise quand même `\r`/`\n`).
4. **Redeploy** : après toute modification de variable, lancer un **Redeploy** du service (les variables runtime ne s’appliquent pas rétroactivement aux conteneurs déjà construits sans redémarrage).
5. **Vérification** : `GET /health` sur l’URL du service → champ `mistral_configured` doit être `true` si la clé est bien injectée.

Sans clé, le service **démarre quand même** (plus de boucle `exit 1` dans `start.sh`) ; les prédictions utilisent le fallback tant que la clé manque.

## Obligatoires (prod)

| Variable | Description |
| --- | --- |
| `MISTRAL_API_KEY` **ou** `DMS_API_MISTRAL` | Clé API Mistral. Sur Railway DMS, le nom **`DMS_API_MISTRAL`** est supporté ; `MISTRAL_API_KEY` reste accepté et **prime** si les deux sont définies. |
| `PSEUDONYM_SALT` | Sel HMAC pour pseudonymisation phone/email en sortie LS |

## Recommandées

| Variable | Description |
| --- | --- |
| `MISTRAL_MODEL` | Défaut : `mistral-small-latest` |
| `CORS_ORIGINS` | URL publique Label Studio (séparateur virgule) ; éviter `*` en prod |
| `MAX_TEXT_CHARS` | Troncature du texte envoyé au LLM (défaut 200000) |
| `MIN_LLM_CONTEXT_CHARS` | Seuil minimum pour appeler Mistral |
| `MIN_PREDICT_TEXT_CHARS` | Seuil côté `/predict` avant refus « texte trop court » |

### Backup local automatique (enterprise anti-perte)

| Variable | Description |
| --- | --- |
| `CORPUS_LOCAL_BACKUP_PATH` | Si défini, active un **`DualCorpusSink`** : le backup local est écrit **en premier** avant S3/R2. Valeur : chemin JSONL absolu ou relatif (ex. `/data/backup/ls_backup.jsonl`). **Recommandé sur Railway** : pointer vers un volume persistant. Si aucun volume : pointer vers un chemin `/tmp` (données perdues au restart mais protège pendant la session). |

> **Pourquoi ?** En cas de déconnexion LS, ou si le webhook S3 échoue, les annotations ne sont pas perdues. 2 semaines de corpus inexploitable = `CORPUS_LOCAL_BACKUP_PATH` non défini.

### Script de sauvegarde locale active (polling)

`scripts/ls_local_autosave.py` — à lancer en tâche de fond sur la machine locale.

```powershell
# Sauvegarde one-shot
python scripts/ls_local_autosave.py --project-id 2 --output data/annotations/ls_autosave.jsonl

# Daemon — sauvegarde toutes les 5 minutes
python scripts/ls_local_autosave.py --project-id 2 --output data/annotations/ls_autosave.jsonl --loop --interval 300

# Miroir JSON brut de l’export API (tout ce qui est sur Label Studio, hors conversion M12)
python scripts/ls_local_autosave.py --project-id 2 --write-raw-ls-json

# Uniquement travail soumis (revue qualité sans tout le backlog de tâches vides)
python scripts/ls_local_autosave.py --project-id 2 --only-finished --output data/annotations/ls_finished.jsonl

# Seulement les fiches marquées « validées » dans LS
python scripts/ls_local_autosave.py --project-id 2 --only-finished --only-if-status annotated_validated --output data/annotations/ls_validated.jsonl
```

Variables requises : `LABEL_STUDIO_URL`, `LABEL_STUDIO_API_KEY`, `PSEUDONYM_SALT`, `ALLOW_WEAK_PSEUDONYMIZATION=1`.

Sur ce script, la QA stricte sur `annotated_validated` est **désactivée** par défaut (tout est sérialisé). Pour l’ancien comportement : `--enforce-validated-qa`.

### Débogage « tout ABSENT » / `AMBIG-PARSE_FAILED`

Si les prédictions ressemblent au squelette vide avec `ambiguites: ["AMBIG-PARSE_FAILED"]` et `_meta.routing_source: llm_fallback_unresolved`, le JSON renvoyé par Mistral **n’a pas été parsé** (ou l’appel API a échoué) — ce n’est en général **pas** le modèle qui a « tout rempli à ABSENT ».

| Variable | Description |
| --- | --- |
| `MISTRAL_PARSE_RETRY` | `1` / `true` (défaut) : en cas d’échec de parse, **un second** appel `chat.complete` identique est tenté. `0` / `false` / `no` / `off` : désactiver. |
| `MISTRAL_PARSE_FAILURE_LOG_PREVIEW` | `1` / `true` / `yes` / `on` : en échec de parse, loguer un extrait du début de la réponse brute (**attention PII** — activer seulement pour diagnostiquer). |
| `MISTRAL_PARSE_FAILURE_PREVIEW_CHARS` | Longueur max de l’extrait (défaut 280, plafonné côté code). |

Les logs Railway cherchent `[PARSE] Fallback` (hash + longueur) ou `[MISTRAL] Erreur appel API`.

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
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | Ou `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. Les **deux** ou **aucune** : si aucune, boto3 utilise la chaîne par défaut (rôle IAM, `~/.aws`, etc.) — utile sur AWS sans variables explicites. |
| `S3_REGION` | Région explicite (ex. `eu-west-1` pour **AWS S3**). Si vide et **`S3_ENDPOINT`** est défini (R2, MinIO), le client utilise `auto`. Si endpoint vide (AWS natif), la région n’est pas forcée — utiliser `AWS_DEFAULT_REGION` ou config boto si besoin. |
| `S3_ADDRESSING_STYLE` | Optionnel : `path` ou `virtual` pour forcer le style d’URL S3 ; laisser vide pour R2 (défaut boto3). |
| `S3_PAYLOAD_SIGNING` | Optionnel : `1` / `true` force la signature SigV4 du corps des `PutObject` ; `0` / `false` la désactive. **Sur endpoint R2** (`*.r2.cloudflarestorage.com`), le backend active cette option par défaut pour limiter les erreurs `SignatureDoesNotMatch`. |
| `S3_CORPUS_PREFIX` | Préfixe des clés objet (défaut : `m12-v2`). Idempotence : une clé par `project_id/task_id/annotation_id/content_hash`. |
| `S3_CLOCK_SKEW_AUTO` | `1` / `true` (défaut) : pour `iter_corpus_m12_lines_from_s3` / export JSONL depuis R2, corrige le décalage d’horloge local vs serveur (en-tête HTTP `Date`, même infra Cloudflare que R2) afin d’éviter `RequestTimeTooSkewed` sur la signature SigV4. `0` / `false` : désactiver (CI, tests, machine avec NTP fiable). |

### Backfill (annotations avant branchement R2)

Les annotations déjà présentes dans Label Studio ne sont pas rejouées automatiquement. Pour les pousser vers le bucket (même logique que le webhook) :

```bash
# Depuis la racine du repo, avec les mêmes variables que le backend (+ S3_*)
python scripts/backfill_corpus_from_label_studio.py --project-id <ID> --limit 20
```

`--dry-run` : vérifie la résolution sans `PutObject`. Voir l’en-tête du script pour `--from-export-json`.

Si `CORPUS_WEBHOOK_STATUS_FILTER` est défini, seules les annotations dont le statut LS correspond seront écrites.

**Dépannage R2 / S3** : au démarrage du conteneur, si `CORPUS_SINK=s3` et `S3_BUCKET` est défini, les logs incluent une ligne **`[BOOT][CORPUS] S3/R2 — …`** (région, `r2_host`, `payload_signing`, `credentials=explicit_env|default_chain`, etc.) — l’endpoint est affiché **sans** userinfo ni query/fragment (seulement schéma + hôte + port), **sans** clés d’accès.

Si les logs montrent `SignatureDoesNotMatch` sur `PutObject` :

1. Vérifier que les clés sont des **jetons API R2** (droits objet) ou paires IAM **AWS**, sans espace ni retour ligne en tête/fin (copier-coller Railway).
2. **`S3_ENDPOINT`** = URL exacte du type `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` (sans slash final).
3. Ne pas mélanger une **access key** d’un compte et un **secret** d’un autre ; régénérer les clés dans le dashboard si besoin.
4. Par défaut le client **ne force pas** `path`-style (aligné doc R2). Si besoin (MinIO, etc.) : `S3_ADDRESSING_STYLE=path` ou `virtual`.
5. Sur R2, le client active **par défaut** la signature du corps (`S3_PAYLOAD_SIGNING` implicite) ; en cas de régression avec un autre proxy S3, désactiver avec `S3_PAYLOAD_SIGNING=0`.

### Sécurité webhook

| Variable | Description |
| --- | --- |
| `WEBHOOK_CORPUS_SECRET` | Si défini, le header HTTP `X-Webhook-Secret` doit correspondre exactement ; sinon `401` sur `POST /webhook`. |

## Développement local

| Variable | Description |
| --- | --- |
| `ALLOW_WEAK_PSEUDONYMIZATION` | `1` uniquement en dev si `PSEUDONYM_SALT` absent (non conforme prod). |
