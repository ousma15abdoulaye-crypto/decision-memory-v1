# PR (copier-coller sur GitHub)

**Base :** `main`  
**Compare :** `fix/annotation-couche2-llm-extras-strip`

## Titre proposé

```
fix(annotation-backend): corpus m12-v2 webhook, R2/S3, Docker, LS_URL fallback
```

## Description (corps de la PR)

```markdown
## Résumé

- Dépôt automatique des lignes **m12-v2** après webhook Label Studio (`POST /webhook`), exécution en `BackgroundTasks`, secret optionnel `WEBHOOK_CORPUS_SECRET` + header `X-Webhook-Secret`.
- Modules : `m12_export_line`, `ls_client`, `corpus_sink` (noop / fichier / S3-compatible), `corpus_webhook`.
- Repli **`LS_URL` / `LS_API_KEY`** si `LABEL_STUDIO_URL` / `LABEL_STUDIO_API_KEY` absents.
- **Pas d’écriture** si `project_id` introuvable (évite collisions de clés S3).
- **S3** : région omise pour endpoint AWS par défaut ; `auto` uniquement avec `S3_ENDPOINT` (ex. R2).
- **Docker** : `COPY` de tout `services/annotation-backend/` ; import paresseux de `corpus_webhook` au boot.
- Script `export_ls_to_dms_jsonl` réutilise `m12_export_line` ; tests `test_corpus_webhook`, `test_export_ls_m12_v2` ; doc `ENVIRONMENT.md`, `M12_EXPORT.md`.

## Merge

À fusionner **via cette PR** (CI : pas de push direct sur `main`).

## Vérifs post-merge

- Redéploiement Railway avec **Root Directory = racine du repo** ; rebuild sans cache si besoin.
- Variables : `CORPUS_WEBHOOK_ENABLED`, `CORPUS_SINK`, R2/S3, `LS_URL`/`LS_API_KEY` ou `LABEL_STUDIO_*`, `LABEL_STUDIO_PROJECT_ID` si besoin.
```
