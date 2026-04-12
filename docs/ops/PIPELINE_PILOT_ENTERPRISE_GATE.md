# Gate pilote entreprise — pipeline V5 / Pass -1 / matrice comparative

**Objectif** : fermer le système pour un pilote **≥ 9 bundles fournisseur** avec preuves traçables, sans revendiquer une généralisation « 100 % terrain » non démontrée.

**Références** : [`docs/ops/GCF_ZIP_E2E_RUNBOOK.md`](GCF_ZIP_E2E_RUNBOOK.md), [`docs/ops/MATRICE_EVALUATION_FRAME_INVESTIGATION.md`](MATRICE_EVALUATION_FRAME_INVESTIGATION.md), [`src/assembler/graph.py`](../../src/assembler/graph.py).

---

## Phase 0 — Cadrage (à signer CTO / produit)

### 0.1 Sémantique « offre » vs « bundle »

| Concept | Définition pilote (à figer) |
|--------|----------------------------|
| **Offre métier** | Ce que l’utilisateur compte (ex. 9 soumissionnaires distincts). |
| **Bundle DMS** | Ligne `supplier_bundles` = regroupement de documents pour une colonne de la matrice. |
| **Cible pilote** | Idéalement **1 offre = 1 bundle** ; si écart, règle explicite (lots, sous-traitants) documentée côté produit. |

**Convention ZIP recommandée** : une entrée par fournisseur sous forme `NomFournisseur/fichier.ext` à la racine du ZIP. Le Pass -1 utilise le **premier segment de chemin** comme clé de bundle (voir `resolve_bundle_vendor_key` dans `graph.py`). Fichiers **sans** dossier parent : heuristique historique (lignes texte SARL/SA + préfixe nom de fichier).

**Cas limites** : même raison sociale sur plusieurs dossiers ; plusieurs lots pour un même fournisseur — trancher : fusion UI, règle d’import, ou acceptation multi-bundles documentée.

### 0.2 Doctrine `DMS_PASS1_HEADLESS`

| Règle | Contenu |
|-------|---------|
| Défaut | Variable **absente** = comportement HITL normal (`interrupt()` si bundles incomplets). |
| Autorisé | **CI**, **scripts E2E locaux**, jobs **non interactifs** explicitement documentés. |
| Interdit sans décision | **Production / Railway** partagée si le contournement masque des dossiers incomplets. |
| Traçabilité | Log **`PASS1_HITL_BYPASS`** + métrique **`dms_pass1_hitl_bypass_total`** (voir `pipeline_v5_metrics`). |
| Si bypass détecté en prod | Procédure : incident, désactivation du flag, reprise HITL — **sauf** exception CTO écrite. |

### 0.3 Critères de sortie pilote (Definition of Done)

Cocher avant « pilote vert » :

- [ ] **≥ 9** `supplier_bundles` avec `vendor_name_raw` **vérifiables** humainement (pas seulement des UUID).
- [ ] Pipeline workspace en statut **completed** (ou équivalent validé).
- [ ] `scores_matrix` : forme M14 détectable (`bundle → criterion` — sonde + doc matrice).
- [ ] **M16** : `criterion_assessments` > 0, alignement clés bundles/critères cohérent avec la matrice.
- [ ] **API** `GET …/evaluation-frame` : `criteria[*].critere_nom` / pondérations lorsque `dao_criteria` existe ; champ **`suppliers`** avec `id` = `supplier_bundles.id`.
- [ ] **UI** : grille comparative relue (checklist § Phase 3).

---

## Phase 1 — Après chaque run pilote

```bash
python scripts/probe_workspace_bundles.py <workspace_uuid>
python scripts/probe_matrix_m14_m16.py <workspace_uuid>
```

Archiver la sortie (ticket / Notion) : comparer **bundles attendus** vs **bundles réels**.

### 1.1 Cause racine des écarts (ex. 9 vs 3)

Les écarts typiques viennent de :

1. **ZIP plat** : chaque fichier devient une clé heuristique différente (`_extract_vendor_name` par document).
2. **Lignes d’en-tête** dans le corps du document : plusieurs « raisons sociales » détectées → plusieurs bundles.
3. **Absence de dossiers** dans le ZIP : la convention § 0.1 n’est pas appliquée.

**Mitigation livrée** : regroupement par **dossier racine** du chemin dans le ZIP quand `chemin` contient au moins deux segments.

---

## Phase 2 — Matrice corpus stress

| # | Profil | Objectif | Critères attendus (à remplir) |
|---|--------|----------|--------------------------------|
| 1 | Propre structuré | Référence | Nb bundles : ___ ; formats : ___ |
| 2 | Sale / bruit | Robustesse | Nb bundles : ___ ; erreurs OCR OK ? |
| 3 | PDF / volume | Charge | Durée max : ___ ; échecs extraction : ___ |

### 2.1 Fiche run (copier par exécution)

| Champ | Valeur |
|-------|--------|
| Date | |
| Workspace ID | |
| Corpus | |
| Durée (s) | |
| Statut pipeline | |
| `supplier_bundles_count` | |
| Erreurs extraction (extrait logs) | |
| Lignes M16 (`n`) | |
| `evaluation_documents` présent ? | |
| Pass / fail | |

*Pass/fail ne constitue pas une preuve « 100 % global » : tableau par scénario.*

---

## Phase 3 — Comparatif

### 3.1 Alignement API (vérifié en implémentation)

- Forme M14 : critères = **union des clés niveau 2** ; enrichissement **`dao_criteria`**.
- Colonnes fournisseurs : **`suppliers`** = `{ id, name }[]` aligné `supplier_bundles`.

### 3.2 Checklist UI (workspace pilote)

- [ ] Libellés fournisseurs lisibles (pas uniquement troncature UUID).
- [ ] Lignes critères : noms + pondérations cohérents avec la DAO.
- [ ] Cellules vides : distinguer « vrai trou » vs filtre client.
- [ ] Écarts notés pour backlog front.

---

## Phase 4 — SLO pilote & CI

### 4.1 SLO indicatifs (à ajuster CTO)

| Métrique | Cible pilote (exemple) |
|----------|-------------------------|
| Durée run 9 bundles (docx, réseau nominal) | &lt; 600 s (ordre de grandeur — mesurer Phase 2) |
| Taux d’échec extraction fatal | 0 sur corpus « propre » ; documenté sur « sale » |
| Bundles sans document | 0 |

### 4.2 CI / PR

- Workflow **manuel** : [`.github/workflows/pipeline_gcf_e2e_dispatch.yml`](../../.github/workflows/pipeline_gcf_e2e_dispatch.yml) — déclenché par `workflow_dispatch`, `DMS_PASS1_HEADLESS=1` **uniquement** dans le job, jamais par défaut sur l’app.
- Merge : pas d’activation headless sur déploiement sans revue ops.

### 4.3 Livraison Git (opérateur)

Si `git push` échoue depuis l’agent (réseau) : pousser manuellement la branche feature, ouvrir la PR, attendre CI verte.

---

## Historique

| Version | Date | Changement |
|---------|------|------------|
| 1.0 | 2026-04-12 | Création — consolidation plan pilote produit. |
