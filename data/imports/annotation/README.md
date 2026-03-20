# data/imports/annotation/ — Corpus PDF pour annotation (offres / DAO)

## Règle (identique en esprit à `data/imports/m4/`)

- Les **fichiers lourds** (PDF) **ne sont pas** « dans » le Markdown : ils vivent **dans ce dossier** (ou un chemin absolu que tu documentes).
- Le Markdown (`test_annotation_doc.md` à la racine, ou ce README) sert de **source de vérité documentaire** : noms, chemins, rôle de chaque fichier.
- **Ne pas committer** de PDF sensibles ou volumineux sans décision explicite (voir `.gitignore` : PDFs sous ce dossier ignorés).

---

## Dépôt des fichiers

```text
data/imports/annotation/
  README.md          ← ce fichier (versionné)
  .gitkeep
  (tes PDF ici — non versionnés par défaut)
```

Exemple de commande d’ingestion vers Label Studio (hors repo) :

```powershell
python scripts/ingest_to_annotation_bridge.py `
  --source-root "data/imports/annotation" `
  --output-root "$env:USERPROFILE\Desktop\DMS_ANNOTATION_OUTPUT" `
  --limit 100
```

---

## Table d’inventaire (à remplir)

| Fichier | Rôle (offre / DAO / TdR) | `document_role` cible | Notes |
|---------|---------------------------|------------------------|-------|
| *(ex.)* `PADEM-offre-financiere.pdf` | offre | `financial_offer` | … |

Copie aussi cette table dans `test_annotation_doc.md` si tu préfères un seul carnet de bord.

---

## Référence mercuriale (même pattern)

- Script mercuriale : chemins déclarés dans `scripts/import_mercuriale.py` (`data/imports/m5/...`).
- Import M4 : noms exacts documentés dans `data/imports/m4/README.md`.

Ici : **tu déposes les PDF**, **tu listes les noms** dans le tableau (ou le carnet), **tu lances le bridge** ou un script métier.

---

## Sécurité

```text
PDF d’appels d’offres / offres : données souvent sensibles ou confidentielles.
Ne pas committer sans anonymisation / accord.
Ne pas coller de contenu binaire dans les fichiers .md.
```
