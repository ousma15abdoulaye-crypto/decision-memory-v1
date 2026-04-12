# Runbook — E2E GCF (3 offres) → Pass -1 → pipeline V5 → matrice

## Artefacts

| Fichier | Rôle |
|---------|------|
| `data/test_zip/gcf_three_offers.zip` | 3 offres (BATE, CRECOS, FETE IMPACTE), extensions autorisées `zip_validator` |
| `data/test_zip/gcf_three_offers_docx_only.zip` | Même corpus, **.docx seulement** (évite OCR PDF si Mistral/Azure KO) |
| `scripts/e2e_gcf_offers_pipeline_matrix.py` | Création workspace + critères 55/45 % + Pass -1 + `run_pipeline_v5` + sonde matrice |
| `scripts/probe_matrix_m14_m16.py` | Sonde SQL M14 vs M16 pour un `workspace_id` |
| `scripts/probe_workspace_bundles.py` | Détail des `supplier_bundles` (P0 bundling : M bundles vs N offres) |

## Construction du ZIP

```bash
python scripts/e2e_gcf_offers_pipeline_matrix.py --build-only
python scripts/e2e_gcf_offers_pipeline_matrix.py --build-only --docx-only
```

Source : `data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/GCF/`.

Exclus automatiquement : `.odt`, `.txt`, `.msg`, etc. Non autorisés par `src/assembler/zip_validator.py`.

## Exécution E2E

Prérequis : `DATABASE_URL`, migrations, utilisateur `admin`, **API Mistral / OpenRouter joignable** (pipeline V5 — extractions async), délai selon `ANNOTATION_TIMEOUT`.

```bash
python scripts/e2e_gcf_offers_pipeline_matrix.py --docx-only --no-cleanup
```

- **`--no-cleanup`** : garde le workspace pour Grafana / `GET /evaluation-frame` / sonde.
- Par défaut le script pose **`DMS_PASS1_HEADLESS=1`** le temps du Pass -1 pour éviter le blocage LangGraph **`interrupt()`** quand la complétude bundle &lt; 0,6 (types `offer_combined`, `nif`, `rccm` manquants sans PDF). **`--strict-hitl`** désactive ce contournement (comportement prod interactif).
- Variable **`DMS_PASS1_HEADLESS`** est lue dans `src/assembler/graph.py` (`hitl_check_node`) — **ne pas activer en prod** sans processus de reprise HITL.
- Quand le bypass s’applique, un log **`PASS1_HITL_BYPASS`** (niveau WARNING) est émis avec `workspace_id`, et le compteur Prometheus **`dms_pass1_hitl_bypass_total`** est incrémenté (si `prometheus_client` est installé). Filtrer ces signaux dans Loki / alertes pour éviter tout contournement silencieux.

## Défaillances observées (Windows / réseau)

| Symptôme | Piste |
|----------|--------|
| `bundle_ids: []` sans `error` | HITL LangGraph sans reprise → utiliser le script E2E (headless) ou enrichir le ZIP (PDF avec indices NIF/RCCM/offre). |
| `SSL: CERTIFICATE_VERIFY_FAILED` (OCR Mistral) | Chaîne de certificats Python Windows ; `pip install certifi` + `SSL_CERT_FILE` ou exécuter depuis Linux/CI. |
| `[EXTRACT] Connexion KO — ConnectError` | Pas de reach vers l’API LLM configurée (firewall, clé, endpoint). |
| `no_bundle_raw_text` (pipeline) | Pass -1 n’a pas produit de texte brut exploitable (bundles vides ou extractions vides). |

## Après coup

```bash
python scripts/probe_matrix_m14_m16.py <workspace_id>
python scripts/probe_workspace_bundles.py <workspace_id>
```

Vérifier `scores_matrix_analysis.shape_guess`, `supplier_bundles_count`, présence d’`evaluation_documents`. La deuxième sonde sert à l’analyse **P0 produit** : pourquoi le moteur produit *M* bundles alors que le dossier métier compte *N* offres (heuristique fournisseur dans `graph.py`).

---

## Statut formulé rigoureusement

> Le pipeline V5 a été prouvé en exécution réelle sur un corpus GCF en mode headless : Pass -1, M14 et M16 traversent, avec matrice persistée de forme canonique (`bundle → criterion`). Les points ouverts avant généralisation produit sont le **bundling** (nombre de bundles vs nombre d’offres attendu) et la **doctrine** du mode headless vis-à-vis du HITL.

Ce n’est pas une preuve de robustesse terrain générale (multi-corpus, charge, reproductibilité, qualité métier des scores) : c’est une **preuve de corridor forte** sur un jeu documentaire réel-ish.

---

## Gouvernance CTO — `DMS_PASS1_HEADLESS`

| Acceptable | À éviter |
|------------|----------|
| Désactivé par défaut (variable absente) | Activé sur Railway / prod sans décision explicite |
| Réservé CI, E2E, batch non interactif | Utilisé pour « faire passer » des dossiers incomplets sans traçabilité |
| Documenté comme continuité technique de test | Présenté comme comportement métier normal |
| Logs / métriques visibles quand le bypass s’applique | Rustine structurelle masquant le HITL |

Toute mise en prod ou sur environnement partagé doit préciser : environnements autorisés, revue ops, et éventuellement règle d’alerte sur `PASS1_HITL_BYPASS` ou `dms_pass1_hitl_bypass_total`.

---

## P0 — Bundling (ex. 9 bundles pour 3 offres)

Si le produit attend « une offre = un bundle », l’écart vient du regroupement actuel (lignes détectées dans le texte, préfixe de nom de fichier, graphe Pass -1). **Analyser** avec `probe_workspace_bundles.py` : `vendor_name_raw`, `bundle_index`, `document_count`, `completeness_score`, puis trancher bug vs règle implicite à documenter ou corriger.
