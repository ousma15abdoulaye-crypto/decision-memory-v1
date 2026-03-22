# PR — copier-coller sur GitHub

**Base :** `main`  
**Compare :** `fix/annotation-couche2-llm-extras-strip`

Ce fichier décrit **toute la branche** (plusieurs sujets peuvent être regroupés). Adapter le **titre** si tu ne merges qu’une partie — ou garde un titre large si la PR reste un seul merge.

---

## Titre proposé (aligné nom de branche + backend)

```
fix(annotation): couche2 LLM extras strip — déploiement annotation-backend (Docker, corpus)
```

Variante plus courte :

```
fix/annotation-couche2-llm-extras-strip
```

---

## Description (corps de la PR)

```markdown
## Portée de la branche

### 1. Sujet nominal (nom de branche)

- Ajustements **annotation / couche 2** et **extraits LLM (strip)** — voir le diff sur les fichiers concernés hors `services/annotation-backend/` si présents.

### 2. Annotation-backend (déploiement & corpus, si inclus dans le même merge)

- **Docker** : copie de tout le dossier `services/annotation-backend/` dans l’image (évite `ModuleNotFoundError` pour les modules ajoutés) ; rappel : contexte de build = **racine du dépôt**.
- **Boot** : import paresseux de `corpus_webhook` ; exécution du traitement corpus **uniquement si** `CORPUS_WEBHOOK_ENABLED` est activé (pas d’import du module quand la fonctionnalité est off).
- **Corpus m12-v2** (optionnel prod) : webhook `POST /webhook`, `BackgroundTasks`, sinks S3/R2/fichier, repli `LS_URL`/`LS_API_KEY`, skip si `project_id` introuvable, doc `ENVIRONMENT.md` / `M12_EXPORT.md`, tests associés.

## Merge

Via **Pull Request** uniquement (CI : pas de push direct sur `main`).

## Post-merge (annotation-backend + corpus)

- Railway : root directory = racine repo ; rebuild sans cache si besoin.
- Si corpus activé : variables `CORPUS_*`, `S3_*`, `LS_URL`/`LS_API_KEY` ou `LABEL_STUDIO_*`, `LABEL_STUDIO_PROJECT_ID` si besoin.
```
