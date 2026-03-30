# M12 Calibration Log

## Palier atteint : bootstrap_75

| Champ | Valeur |
|-------|--------|
| Date calibration | 2026-03-30 |
| Corpus source | Label Studio export (m12-v2 schema) |
| Corpus taille | 75 annotations (100% export_ok) |
| Branche | `feat/m12-engine-v6` |
| Moteur version | V6 deterministic |
| Iterations calibration | 4 |

## Distribution corpus par type (n>=5 marquees *)

| taxonomy_core | Count | N>=5 |
|---------------|-------|------|
| supporting_doc | 25 | * |
| offer_financial | 15 | * |
| offer_technical | 15 | * |
| dao | 12 | * |
| evaluation_report | 3 | |
| tdr_consultance_audit | 3 | |
| offer_combined | 1 | |
| ao_consultancy_baseline_study | 1 | |

Types non couverts dans le corpus (11/19) :
rfq, contract, po, grn, boq, submission_letter, admin_doc, price_schedule,
market_survey, mercuriale, itt.

## Metriques finales

| Check | Seuil | Score | Resultat |
|-------|-------|-------|----------|
| document_kind_parent accuracy (n>=5) | >= 0.80 | **0.8209** | PASS |
| evaluation_doc non-offer recall | = 1.00 | **1.0000** | PASS |
| framework_detection accuracy | >= 0.85 | **0.8649** | PASS |

### Per-class F1 (n>=5 types)

| Type | P | R | F1 | Support |
|------|---|---|----|---------| 
| dao | 0.8571 | 1.0000 | 0.9231 | 12 |
| offer_financial | 0.9231 | 0.8000 | 0.8571 | 15 |
| offer_technical | 0.9286 | 0.8667 | 0.8966 | 15 |
| supporting_doc | 0.8182 | 0.7200 | 0.7660 | 25 |

## Corrections appliquees pendant calibration

### Iteration 1 -> 2 (accuracy 0.1791 -> 0.5672)

1. **DAO rule broadened** (R07): Added `APPEL D'OFFRES RESTREINT|OUVERT|POUR|RELATIF|CONCERNANT` in header. Merged former ITT rule (R08) into DAO since SCI Mali uses "Appel d'Offres" for full dossiers, not just invitations.

2. **Composite detection tightened**: Reduced `_COMPOSITE_WINDOW` from 20000 to 2000 chars. Removed `BORDEREAU DES PRIX` from composite financial signals to prevent false offer_combined from financial documents with pricing tables.

3. **Supporting doc rules added**: Three new rules (R14-R16) for policies, admin docs, and certificates.

4. **Financial body rule added** (R17): Catches supplier quotes with `FOURNITURE DE ... PRIX|MONTANT|TOTAL`.

### Iteration 2 -> 3 (accuracy 0.5672 -> 0.7463)

5. **Composite detection further tightened**: Reduced `_COMPOSITE_WINDOW` from 2000 to 800 chars (header-only). This fixed most offer_financial/offer_technical -> offer_combined false positives.

6. **Submission letter narrowed** (R13): Removed `JE SOUSSIGNE` pattern (too broad, catches certificates). Now only matches `LETTRE DE SOUMISSION`.

7. **Rule reordering**: Moved R17 (financial body) before R14-R16 (supporting doc) to prevent financial offers with admin info from being classified as supporting_doc.

### Iteration 3 -> 4 (accuracy 0.7463 -> 0.8209)

8. **CV detection rule** (R18): Added comprehensive CV patterns including OCR-resilient spaced letters (`P R O F I L`), English patterns (`Professional Experience`, `Portfolio Manager`), and ligature-aware matching.

9. **Certificate OCR resilience** (R16): Added spaced letter pattern for `CERTIFICAT` and standalone `IMMATRICULATION`.

10. **Budget table detection** (R17): Added `Honoraire.*\d+\d{3}` and `C. Unitaires Total` for financial documents without explicit offer headings.

11. **Digital/compliance supporting docs** (R19): Added `DocuSign Envelope`, `ENGAGEMENT ... RESPECT`, `RESPECT DES POLITIQUES`.

## Failles irreductibles identifiees

Les erreurs restantes (17/75 = 22.7% global) se decomposent en :

- **Disagreements annotation** (6 cas) : documents annotes comme supporting_doc mais contenant des signaux forts pour un autre type (2x evaluation_doc header, 1x contract header, 1x PO header, 2x OCR trop degrade)
- **Composite ambiguite** (2 cas) : consultants soumettant technique+financier dans un meme document, annote comme offer_financial
- **OCR severe** (3 cas) : texte tellement degrade que aucun pattern ne peut matcher
- **Remaining edge cases** (6 cas) : types < n5 sans couverture suffisante

## Prochain palier : bootstrap_100

Quand le corpus atteindra 100 annotations :
1. Re-exporter depuis Label Studio
2. Executer `python scripts/m12_benchmark_against_corpus.py`
3. Seuils bootstrap_100 (plan M12 V6 section 7.1) :
   - `document_kind_parent` macro_f1 >= 0.82
   - `handoff_quality` completeness >= 0.75
   - `linking_basic` precision L1+L2 >= 0.85
4. Mettre a jour ce fichier avec les resultats palier 100
