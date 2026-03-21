# Politique d’export ground truth — M15 (pré-entraînement)

**Statut :** politique produit / export — complète l’export M12 sans le remplacer.  
**Gel formel :** ce fichier n’est **pas** référencé dans [`FREEZE_HASHES.md`](FREEZE_HASHES.md) ; il ne constitue pas un document « opposable » au sens [ADR-META-001-AMENDMENT-PROCESS.md](./ADR-META-001-AMENDMENT-PROCESS.md) tant qu’aucun enregistrement append-only de hash n’a été effectué.  
**Références :** [ADR-M12-EXPORT-V2.md](../adr/ADR-M12-EXPORT-V2.md), [`src/annotation/m12_export_io.py`](../../src/annotation/m12_export_io.py), schéma `DMSAnnotation` v3.0.1d.

## Portée

Ce document définit **quels enregistrements** peuvent entrer dans un corpus JSONL destiné au **pré-entraînement (M15)**.  
Ce n’est **pas** une preuve de précision métier globale : toute prétention de gate F2 stable exige une **baseline réelle** sur corpus.

La **vérité terrain** reste **humaine** (`annotated_validated`) ; le pipeline et les politiques ci-dessous **filtrent le bruit**, ils ne substituent pas l’annotateur.

## Critères d’inclusion

Une ligne (ou un document) **entre** dans le JSONL M15 si **toutes** les conditions suivantes sont satisfaites :

1. `annotation_status` = `annotated_validated` (ou équivalent export LS aligné sur M12).
2. `review_required` = `false` dans `_meta` après export (ou champ équivalent dans `ls_meta` si dérivé).
3. `routing_source` ∈ `{ deterministic_classifier, llm_fallback_validated }` (champs `_meta` produits par ARCH-02).
4. `taxonomy_core` ≠ `unknown`.
5. Aucune ligne `line_items[*].line_total_check` = `ANOMALY` **non résolue** (soit corrigée en validation humaine, soit document exclu).
6. Pour tout champ avec `confidence` &lt; 1.0 dans les blocs concernés, `evidence` est **non vide** et cohérent avec la politique evidence du validateur / export M12.

## Critères d’exclusion

Un enregistrement est **rejeté** du corpus M15 si **au moins une** condition est vraie :

1. `annotation_status` ≠ `annotated_validated`.
2. `review_required` = `true` (y compris règles ARCH-04 : pièces admin absentes, anomalie arithmétique, ligne vide sur offre financière, montant &gt; seuil de prudence).
3. `routing_source` = `llm_fallback_unresolved` ou `taxonomy_core` = `unknown`.
4. Plus de **20 %** des `line_items` ont `line_total_check` = `ANOMALY` (seuil de densité d’erreur — ajustable par décision produit).
5. `export_ok` = `false` sur la ligne M12-v2 (voir ADR-M12-EXPORT-V2) ou échec `validate_annotation.py` sur l’extrait correspondant.

## Format d’export

- **JSONL** : une ligne JSON par document / tâche exportée.
- **Traçabilité obligatoire** : `content_hash` / `sha256` du contenu source ou de l’extrait canonique (aligné M12).
- **`schema_version`** ou `export_schema_version` : documenter explicitement `v3.0.1d` / `m12-v2` selon le pipeline d’export utilisé.
- Préférer les champs **`dms_annotation`** + **`ls_meta`** du contrat M12-v2 pour éviter la dérive de schéma.

## Audit humain avant scale

Avant de dépasser **500** annotations dans le JSONL M15 cumulé :

1. Tirer **50** enregistrements au hasard (stratifiés par `taxonomy_core` si possible).
2. Relecture humaine ciblée : `couche_1_routing`, `line_items`, `evidence` vs texte source.
3. **Seuil d’erreur** : si le taux d’erreur matérielle dépasse **5 %** sur l’échantillon → **STOP produit** : ne pas scaler le volume ; investiguer prompt, validateur, ou consigne d’annotation.
4. Documenter les écarts **systématiques** (ex. même gate, même type de ligne) pour calibration.

## Accord inter-annotateurs (signal de calibration)

Sur les **50** fiches d’audit :

- Comparer corrections humaines vs sortie pipeline à l’export.
- Ce n’est **pas** un gate CI bloquant par défaut ; c’est un **signal** pour ajuster consigne, LOI prompt, ou seuils de review.

## Application opérationnelle

Cette politique est la **loi d’inclusion M15** ; elle n’est **pas** exécutée automatiquement par le seul backend `/predict`.  
Recommandation : faire appliquer ces règles par le **script d’export** (`export_ls_to_dms_jsonl` / filtre post-`m12_export_io`) et/ou une **étape CI** sur un échantillon avant publication du corpus.

## Seuil financier « montant élevé »

Le seuil configurable côté backend (`FINANCIAL_REVIEW_THRESHOLD_XOF`, défaut 10 000 000) est une **règle locale de prudence** ; il ne constitue pas un invariant juridique universel. Toute réutilisation dans ce document pour l’exclusion M15 doit **référencer** explicitement `_meta.review_required` et `review_reasons`, pas seulement le montant brut.

---

*Révision initiale : implémentation plan entreprise annotation (ARCH-02 → ARCH-04 + DATA-M15).*
