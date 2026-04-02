# ADR-M13-001 — Regulatory Profile Engine (M13 V5)

**Statut :** Accepté (implémentation)  
**Date :** 2026-04-02  
**Référence spec :** DMS-M13-V5-FREEZE (plan d’exécution consolidé)

## Contexte

M13 applique un régime réglementaire **100 % déterministe** à partir de YAML et des sorties M12 (H1 `RegulatoryProfileSkeleton`, reconnaissance procédure, gates). M14 reste responsable du scoring et des verdicts d’offre.

## Décisions

### 1. Deux niveaux de rapport de conformité

- **`RegulatoryComplianceReport`** dans [`src/procurement/compliance_models.py`](../../src/procurement/compliance_models.py) : **résumé legacy** (verdict + checks éliminatoires) — **conservé** pour compatibilité contrat historique.
- **`M13RegulatoryComplianceReport`** dans [`src/procurement/compliance_models_m13.py`](../src/procurement/compliance_models_m13.py) : **rapport moteur V5** (R1–R4, principes, OCDS, méta).  
- Pont : **`legacy_compliance_report_from_m13()`** produit le modèle legacy à partir du bundle M13 (`M13Output`).

### 2. Confiance contractuelle {0.6, 0.8, 1.0}

Toute **confidence** exposée dans les modèles M13 respecte la grille DMS :

| Situation | Valeur |
|-----------|--------|
| Règle réglementaire chargée depuis YAML (obligatoire) | 1.0 |
| Correspondance document ∩ réglementation (min des deux entrées) | min(m12, 0.8) discrétisé |
| Inférence / dégradé UNKNOWN / bootstrap | 0.6 |
| Intermédiaire | 0.8 |

Les valeurs du spec V5 (0.30, 0.95, etc.) sont **mappées** à cette grille dans le moteur ; elles ne sortent pas brutes dans les payloads JSON.

### 3. Persistance

- **Ne pas** stocker le profil M13 dans `evaluation_documents` (056) : table réservée au cycle ACO / comité ( `committee_id` NOT NULL, scores).
- **Nouvelle table** `m13_regulatory_profile_versions` : `case_id`, `version`, `payload` JSONB, RLS `tenant_scoped` via `cases.tenant_id` (même principe que 056).
- **`m13_correction_log`** : append-only, symétrique à `m12_correction_log` (054).

### 4. `regulatory_index` (JSON parsés)

**Pas de duplication** des règles : la résolution opérationnelle utilise **`RegulatoryConfigLoader`** + YAML sous `config/regulatory/`. L’index existant [`src/procurement/regulatory_index.py`](../../src/procurement/regulatory_index.py) reste disponible pour **audit / traçabilité** (références croisées), pas comme source parallèle de seuils.

### 5. Interdictions (STOP signals)

- Pas de LLM dans M13 ; pas de `verification_method` équivalente à une inférence LLM — utiliser `manual_review` ou `document_presence` pour les cas nécessitant humain.
- Pas de second orchestrateur : extension de [`src/annotation/orchestrator.py`](../../src/annotation/orchestrator.py) + flag `ANNOTATION_USE_PASS_2A`.

### 6. Migration Alembic

- **`057_m13_regulatory_profile_and_correction_log`** : uniquement nouvelles tables + politiques RLS ; chaîne `056 → 057`.

## Conséquences

- Mise à jour des contrats [`M12_M13_HANDOFF_CONTRACT.md`](../contracts/annotation/M12_M13_HANDOFF_CONTRACT.md), [`PASS_2A_REGULATORY_PROFILE_CONTRACT.md`](../contracts/annotation/PASS_2A_REGULATORY_PROFILE_CONTRACT.md), [`M13_M14_HANDOFF_CONTRACT.md`](../contracts/annotation/M13_M14_HANDOFF_CONTRACT.md).
- CI : alignement `VALID_ALEMBIC_HEADS` / `validate_mrd_state` / `probe_alembic_head` après merge de 057.
