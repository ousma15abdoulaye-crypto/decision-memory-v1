# M12 — Smoke infra annotation (Phase A)

Checklist avant d’engager les 15 documents AO. Réf. : [PIPELINE_REFONTE_FREEZE.md](../freeze/PIPELINE_REFONTE_FREEZE.md), [CONTEXT_ANCHOR.md](../freeze/CONTEXT_ANCHOR.md).

## 1. Label Studio (Railway)

- [ ] Service **label-studio-dms** (ou équivalent) **running** (pas de crash loop).
- [ ] PostgreSQL dédié LS : variable **`POSTGRE_PORT=5432`** si `${{Postgres-LS.PGPORT}}` pose problème (voir CONTEXT_ANCHOR).
- [ ] Healthcheck `/health` OK (depuis Railway ou navigateur).
- [ ] Projet créé avec labeling config alignée sur [`services/annotation-backend/label_studio_config.xml`](../../services/annotation-backend/label_studio_config.xml).

## 2. Annotation backend (ML)

URL notée : `ANNOTATION_BACKEND_URL` (ex. service Railway séparé).

Variables obligatoires :

| Variable | Rôle |
|----------|------|
| `MISTRAL_API_KEY` | Appel Mistral |
| `MISTRAL_MODEL` | ex. `mistral-small-latest` |
| `PSEUDONYM_SALT` | Sel HMAC (ou `ALLOW_WEAK_PSEUDONYMIZATION=1` **dev uniquement**) |
| `CORS_ORIGINS` | URL **publique** de Label Studio (ex. `https://xxx.up.railway.app`) ou `*` en debug |

Vérifications :

- [ ] `GET {ANNOTATION_BACKEND_URL}/health` → JSON `status: ok`
- [ ] `POST {ANNOTATION_BACKEND_URL}/setup` → `status: ready`

## 3. Liaison LS → backend

- [ ] Dans LS : **Settings → Machine Learning** : URL du backend + même schéma de labeling (`document_text`, `extracted_json`).
- [ ] **Test** : ouvrir une tâche avec texte non vide → **Predict** → le champ **extracted_json** contient du JSON (pas vide).

## 4. Script automatisé (optionnel)

Avec `ANNOTATION_BACKEND_URL` défini :

```powershell
python scripts/smoke_m12_annotation.py
```

Exit `0` : health + `/predict` minimal OK ou skip si URL absente (CI-friendly).

## Critère de sortie Phase A

Une prédiction ML remplit le textarea **extracted_json** pour au moins une tâche réelle.
