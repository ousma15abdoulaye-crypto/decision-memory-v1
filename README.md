# DMS — Decision Memory System (V3.3.2)

DMS est un système **procurement** en 2 couches conçu pour **accélérer** et **standardiser** un travail manuel (DAO/RFQ/RFP → extraction → normalisation → scoring → exports CBA/PV), tout en construisant une **mémoire décisionnelle** exploitable (Market Signal / Market Survey) **sans jamais prescrire** la décision.

> DMS ne signe pas de contrat, n’émet pas de bon de commande et ne remplace pas un comité.  
> Il **calcule**, **structure**, **trace**, puis **exporte** vers les livrables officiels (Excel/Word).  
> La décision finale reste humaine et traçable.

---

## Pourquoi DMS existe

Dans beaucoup d’organisations, le procurement devient lent et opaque non pas parce que les règles n’existent pas, mais parce que :
- elles sont dispersées (memos, manuels, habitudes),
- elles sont réappliquées manuellement (Excel + copier/coller),
- l’audit trail est incomplet ou “SharePoint-like” (documents, mais pas une mémoire vivante).

DMS formalise un “atelier” (Couche A) et une “mémoire” (Couche B) pour que l’organisation respire : **plus rapide**, **plus cohérent**, **plus auditable**.

---

## Architecture (2 couches)

### Couche A — Atelier d’exécution (procédural, autonome)
Responsable de :
- ingestion de documents (DAO/RFQ/RFP…)
- extraction (texte/structures)
- normalisation via dictionnaire procurement (non contournable)
- scoring multi-critères
- génération / export **CBA Excel** + **PV Word**
- registre de dépôt (append-only)
- comité (configuration → validation → **LOCK irréversible**)

**Couche A est autonome** : elle doit pouvoir produire les livrables sans Couche B.

### Couche B — Mémoire & Market Signal (non prescriptive)
Responsable de :
- Market Signal à 3 sources (mercuriale / historique / market surveys)
- explications contextuelles (aide à la compréhension)
- audit vivant : traces, corrections, historique, justification

**Couche B n’influence jamais les scores.**  
Elle éclaire, elle ne décide pas.

---

## Principes non négociables

La référence officielle est la Constitution :

- `docs/CONSTITUTION_DMS_V3.3.2.md`
- `docs/INVARIANTS.md`

Exemples de règles “opposables” :
- **Append-only** sur les traces critiques (corrections, registre dépôt, lock events, logs).
- **Aucun scoring sur une offre brute** : normalisation obligatoire.
- **Comité** : une fois **LOCK**, la composition ne change plus (interdiction totale de remplacement/ajout/suppression).
- **Couche B non prescriptive** : pas de recommandations décisionnelles.

---

## Workflow fonctionnel (haut niveau)

1. Création d’un cas (case)
2. Upload des documents
3. Extraction + corrections (append-only)
4. Normalisation via dictionnaire
5. Scoring + tableau comparatif
6. Configuration comité (identités) → **LOCK comité**
7. Export des livrables (CBA/PV)
8. Mémoire & Market Signal consultables (Couche B)

---

## Documentation (où lire quoi)

### Canonique
- Constitution : `docs/CONSTITUTION_DMS_V3.3.2.md`
- Plan milestones : `docs/MILESTONES_EXECUTION_PLAN_V3.3.2.md`
- ADRs : `docs/adrs/ADR-0001.md`

### Références techniques
- **Nouveau PC (OneDrive, clé USB, dossier copié)** : lire `LISEZMOI_NOUVEAU_PC.txt`, puis lancer `premier_demarrage.bat` à la racine (sous Windows, « PREMIER_DEMARRAGE.bat » est le même fichier, casse ignorée) ; procédure détaillée : `docs/dev/LAPTOP_MIGRATION.md` (section « Procédure complète — nouveau PC »).
- Architecture : `docs/ARCHITECTURE.md`
- Schéma DB : `docs/DATABASE_SCHEMA.md`
- API : `docs/API_REFERENCE.md`
- Sécurité : `docs/SECURITY.md`
- SLA / perf : `docs/PERFORMANCE_SLA.md`
- Guide dev : `docs/DEVELOPER_GUIDE.md`
- Guide user : `docs/USER_GUIDE.md`

### Freeze (immutables)
- Index : `docs/freeze/README.md`
- Freeze V3.3.2 : `docs/freeze/v3.3.2/`  
  (manifest + hashes SHA256 + copies des docs)

---

## Structure du repo (indicative)

src/
couche_a/ # ingestion, extraction, normalisation, scoring, exports, UX workspace
couche_b/ # mémoire, market signal/survey, chat/context (non prescriptif)
dictionary/ # colonne vertébrale normalisation (items, unités, vendors)
mapping/ # moteur mapping template CBA (si utilisé)
docs/
adrs/
audits/
freeze/
tests/
invariants/
ux/
mapping/
.github/workflows/


---

## Quickstart (local)

### Pré-requis
- Python 3.11+
- PostgreSQL 15+
- (Optionnel) Docker

### Variables d’environnement
Exemple :
- `DATABASE_URL=postgresql://user:pass@localhost:5432/dms`
- `JWT_SECRET_KEY=...`
- `ENV=dev`

### Installer & lancer
```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

# migrations
alembic upgrade head

# run api (aligné Railway / start.sh — voir docs/audits/SYSMAP_DMS_EXIT_PLAN_01.md)
uvicorn main:app --reload
```

### Tests
```bash
pytest -q
```

### Coverage (si gate activé)
```bash
pytest --cov=src --cov-report=term-missing
```

### CI / qualité
La CI est l’arbitre :

- CI verte obligatoire
- tests invariants (voir `tests/invariants/`)
- gate coverage selon phase (voir plan milestones)
- aucune PR mergée avec CI rouge

### Sécurité (résumé)
DMS implémente / prévoit :

- JWT + RBAC (rôles)
- validation upload (magic bytes, taille, etc.)
- rate limiting
- secrets uniquement via env
- logs structurés + audit log

Détails : [`docs/SECURITY.md`](docs/SECURITY.md)

### Déploiement
Déploiement cible : Railway (PostgreSQL + app). Checklist : [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

### Module — CBA Template Mapping Engine
Si tu utilises le moteur de mapping CBA (pré-large + masquage fournisseurs), la doc module vit hors README racine : [`docs/modules/MAPPING_ENGINE.md`](docs/modules/MAPPING_ENGINE.md) (recommandé) ou `src/mapping/README.md`.

### Licence / propriété intellectuelle
Ce dépôt et son contenu sont une propriété intellectuelle.
L’usage, la reproduction et la redistribution sont soumis aux règles définies par l’auteur.

