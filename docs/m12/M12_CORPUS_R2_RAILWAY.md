# Corpus M12 sur Cloudflare R2 — variables Railway

**Réf.** détaillée : [`services/annotation-backend/ENVIRONMENT.md`](../../services/annotation-backend/ENVIRONMENT.md) (section *Dépôt corpus m12-v2*).  
**Cible** : service **annotation-backend** sur Railway (celui qui expose `/webhook` et écrit le corpus).

---

## État terrain (déjà réalisé chez AO)

**Oui, c’est compris :** le bucket R2 existe, le corpus est créé, les annotations ont été **migrées** dans le bucket (webhook + éventuel backfill). Les clés et variables Railway sont **déjà** posées là où elles doivent l’être pour que ça tourne.

Ce document ne te demande pas de « refaire » le chantier : c’est une **référence** pour audit, reprise après incident, onboarding d’un tiers, ou deuxième environnement — pas une checklist obligatoire pour toi aujourd’hui.

---

## 1. Côté Cloudflare R2

1. **R2** → créer un **bucket** (ex. `dms-m12-corpus` — nom interne à toi).
2. **R2** → **Manage R2 API Tokens** → créer un token avec droits **Object Read & Write** sur ce bucket (ou compte selon ta politique).
3. Noter :
   - **Access Key ID**
   - **Secret Access Key**
   - **S3 API** : URL du type `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` (Dashboard R2 → bucket → *S3 API*).

Ne jamais committer ces valeurs dans le repo.

---

## 2. Côté Railway (annotation-backend)

Dans **Railway** → projet → service **annotation-backend** → **Variables** :

### Activer le webhook corpus + sink S3 (R2)

| Variable | Valeur exemple / règle |
| --- | --- |
| `CORPUS_WEBHOOK_ENABLED` | `1` |
| `CORPUS_SINK` | `s3` |
| `S3_BUCKET` | Nom exact du bucket R2 |
| `S3_ENDPOINT` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` (**sans** slash final) |
| `S3_ACCESS_KEY_ID` | Access Key du token R2 |
| `S3_SECRET_ACCESS_KEY` | Secret du token R2 |
| `S3_REGION` | Laisser **vide** pour R2 (le code utilise `auto` quand `S3_ENDPOINT` est défini). |
| `S3_CORPUS_PREFIX` | Optionnel ; défaut `m12-v2` (préfixe des clés objet) |

**R2 / signature** : pour les hôtes `*.r2.cloudflarestorage.com`, le backend active en général la signature du corps `PutObject`. Si problème : voir `S3_PAYLOAD_SIGNING` dans `ENVIRONMENT.md`.

### Filtrer uniquement les annotations validées (recommandé prod)

| Variable | Valeur |
| --- | --- |
| `CORPUS_WEBHOOK_STATUS_FILTER` | `annotated_validated` |

Ainsi seules les tâches au statut attendu sont écrites dans R2.

### Label Studio (re-fetch si webhook incomplet)

| Variable | Description |
| --- | --- |
| `LABEL_STUDIO_URL` | URL publique de ton instance LS |
| `LABEL_STUDIO_API_KEY` | Token API (`Authorization: Token …`) |
| `LABEL_STUDIO_PROJECT_ID` | ID projet si le payload webhook ne le fournit pas toujours |

### Sécurité

| Variable | Description |
| --- | --- |
| `WEBHOOK_CORPUS_SECRET` | Secret partagé ; LS doit envoyer le même dans `X-Webhook-Secret` sur `POST /webhook` |

### Obligatoires déjà (rappel)

| Variable | Rôle |
| --- | --- |
| `MISTRAL_API_KEY` | Pré-annotation |
| `PSEUDONYM_SALT` | Même valeur que partout où tu pseudonymises (backfill inclus) |

---

## 3. Vérification après déploiement

1. Logs au boot : ligne **`[BOOT][CORPUS] S3/R2 — …`** (endpoint masqué, pas de clés).
2. Déclencher une annotation **annotated_validated** dans LS → webhook → objet sous préfixe `S3_CORPUS_PREFIX` dans le bucket.
3. En cas d’erreur `SignatureDoesNotMatch` : checklist § *Dépannage R2 / S3* dans `ENVIRONMENT.md`.

---

## 4. Backfill (annotations déjà faites avant R2)

Même variables Railway (ou export local `.env` aligné) :

```bash
python scripts/backfill_corpus_from_label_studio.py --project-id <ID_LS> --limit 50
```

Sans écriture : `--dry-run`. Voir en-tête du script pour `--from-export-json`.

---

## 5. API principale DMS (Railway `main:app`)

L’écriture corpus **m12-v2** se fait dans le **annotation-backend**, pas dans l’API `main.py`.  
L’API DMS n’a **pas** besoin des `S3_*` pour ce flux, sauf si tu ajoutes plus tard un autre service qui lit/écrit le même bucket (mandat séparé).
