# M12 — Pipeline industrialisé (anti-perte LS / reprise projet)

## Probleme vecu

Label Studio peut **se deconnecter**, **perdre le contexte projet**, ou imposer un **nouveau projet**. Les objets **R2** sont une copie **asynchrone** (webhook) : `extracted_json` peut etre vide, `dms_annotation` null, `export_ok` false — **R2 seul ne remplace pas** un export LS + sauvegardes locales versionnees.

## Regles operatoires (a respecter)

1. **Verite de travail immédiate** : JSONL produit par `export_ls_to_dms_jsonl.py` + copies dans `data/annotations/backups/` — pas seulement l’UI LS.
2. **Avant chaque session d’annotation** : lancer `scripts/m12_corpus_backup.ps1` (ou au minimum export R2).
3. **Apres chaque session** : meme backup + export LS vers un fichier date (le script le fait).
4. **Nouveau projet LS** : suivre la checklist ci-dessous **avant** d’annoter a nouveau.
5. **Webhook Railway** : doit pouvoir **re-fetch** la tache LS (`LABEL_STUDIO_URL` + token) — sinon le corpus R2 reste partiel.

## Nouveau projet Label Studio — checklist

| Etape | Action |
|-------|--------|
| 1 | Importer / coller le **meme** `services/annotation-backend/label_studio_config.xml` (champs `extracted_json`, `document_text`, attestations, statuts). |
| 2 | Brancher le **ML backend** (URL Railway) dans LS — meme contrat `to_name=document_text` (E-66). |
| 3 | Noter le **nouvel ID projet** ; mettre a jour partout : `LABEL_STUDIO_PROJECT_ID` (Railway + `.ls_export_env` local), scripts d’export. |
| 4 | Reconfigurer le **webhook** LS → `POST https://<annotation-backend>/webhook` avec secret si `WEBHOOK_CORPUS_SECRET` ; actions `ANNOTATION_CREATED,ANNOTATION_UPDATED`. |
| 5 | Variables R2 inchangées si meme bucket ; sinon mettre a jour `S3_*` + prefix `m12-v2`. |
| 6 | Premiere sauvegarde : `.\scripts\m12_corpus_backup.ps1` pour etablir une ligne de base. |

## Scripts (rappel)

| Besoin | Script / doc |
|--------|----------------|
| Export LS → JSONL exploitable DMS | `scripts/export_ls_to_dms_jsonl.py` — voir `docs/m12/M12_EXPORT.md` |
| Export R2 → JSONL | `scripts/export_r2_corpus_to_jsonl.py` (defaut : `data/annotations/m12_corpus_authoritative.jsonl`) |
| Backup date (R2 + LS + copie authoritative) | `scripts/m12_corpus_backup.ps1` |

## Variables d’environnement (synthese)

- **LS** : `LABEL_STUDIO_URL`, `LABEL_STUDIO_API_KEY`, `LABEL_STUDIO_PROJECT_ID` (ou `LS_URL` / `LS_API_KEY`).
- **R2** : `S3_BUCKET`, `S3_ENDPOINT`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, option `S3_CORPUS_PREFIX`, `S3_VERIFY_SSL=0` si TLS entreprise.
- **Webhook corpus** : `CORPUS_WEBHOOK_ENABLED`, `CORPUS_SINK=s3`, `CORPUS_WEBHOOK_ACTIONS`, option `CORPUS_WEBHOOK_STATUS_FILTER` — detail `services/annotation-backend/ENVIRONMENT.md` et `docs/m12/M12_CORPUS_R2_RAILWAY.md`.

## Finir les annotations (nouveau projet)

1. Re-importer les **documents / taches** (bridge ingestion ou import LS selon votre flux).
2. Utiliser **pre-annotation** backend (`/predict`) pour remplir `extracted_json` des le depart (moins de perte si LS coupe).
3. Sauvegarder **souvent** avec `m12_corpus_backup.ps1`.
4. Gate qualite : `scripts/validate_annotation.py` sur le JSONL LS exporte.

## Reference doc existante

- Export & consolidation : `M12_EXPORT.md`
- Infra & smoke : `M12_INFRA_SMOKE.md`
- Multipasses post-gate : `DMS_ANNOTATION_MULTIPASS_POST_M12.md`
