# Bibliothèque réglementaire DMS (SCI + DGMP)

Ce dossier accueille les **sources brutes** et les **extractions structurées** pour alimenter le moteur de profils (M13) et la traçabilité audit.

## Arborescence

| Chemin | Rôle |
|--------|------|
| `raw/` | Déposer ici les PDF / DOCX (manuel SCI, code marchés publics Mali DGMP, arrêtés). **Ne pas committer** les originaux sensibles si politique interne l’exige — ils sont ignorés par git (voir `.gitignore`). |
| `parsed/` | Sortie JSON produite par `scripts/parse_regulatory_docs.py` (texte extrait + structure LLM). Les fichiers `*_library.json` peuvent être versionnés après validation AO. |

## Déposer les fichiers

1. Copier dans `raw/` avec un nom explicite, par exemple :
   - `sci_procurement_manual.pdf` (ou `.docx`)
   - `mali_dgmp_code_marches_publics_2015.pdf`
2. **Clé Mistral (le plus simple)** : copier `MISTRAL_KEY.txt.example` → `MISTRAL_KEY.txt` dans ce dossier et mettre **une seule ligne** = ta clé API (fichier ignoré par git). Alternative : `MISTRAL_API_KEY` dans `.env.local`.
3. Optionnel : `LLAMADMS` ou `LLAMA_CLOUD_API_KEY` — si `--method llamaparse`

Le script positionne `STORAGE_BASE_PATH` sur la racine du dépôt le temps de l’exécution (requis par `src/extraction/engine` pour accepter les chemins sous le repo, notamment sous Windows).

Si tu vois une erreur SSL (`CERTIFICATE_VERIFY_FAILED`), le client Mistral utilise le bundle `certifi` ; en réseau d’entreprise, `IMPORT_REGULATORY.bat` définit `MISTRAL_SSL_VERIFY=0` (désactive la vérification SSL côté client). Une erreur **401 Unauthorized** signifie une **clé API invalide ou expirée** : vérifie la clé sur [La Plateforme Mistral](https://console.mistral.ai) (copier-coller entier, souvent préfixe `…`).

## Lancer l’import

**Windows** : double-cliquer `IMPORT_REGULATORY.bat` à la racine du dépôt (ou lancer la commande ci-dessous).

Depuis la racine du dépôt :

```bash
python scripts/parse_regulatory_docs.py --all --method auto
```

Options utiles :

- `--method auto` — PDF : essai texte local (pypdf) puis Mistral OCR si vide ; DOCX : extraction locale.
- `--method mistral_ocr` — forcer Mistral OCR (PDF/images).
- `--method llamaparse` — forcer LlamaParse (clé Llama requise).
- `--extract-only` — uniquement le texte brut → `parsed/*_extracted.md` (pas d’appel chat structurant).
- `--file raw/mon_fichier.pdf` — traiter un seul fichier.

## Sorties

Pour chaque fichier source `raw/foo.pdf` :

- `parsed/foo_extracted.md` — texte/markdown extrait (intermédiaire).
- `parsed/foo_library.json` — enveloppe DMS : métadonnées, texte tronqué pour audit, et `structured` (sections, seuils, procédures, citations) produit par le modèle.

## Règles

- **RÈGLE-11 / ADR** : toute évolution du pipeline LLM vers la prod doit être couverte par un ADR avant merge applicatif.
- **RÈGLE-21** : les tests CI ne doivent pas appeler les APIs ; le script est conçu pour l’usage local / mandat.
