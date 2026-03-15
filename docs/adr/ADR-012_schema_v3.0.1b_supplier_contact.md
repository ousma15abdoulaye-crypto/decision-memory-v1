# ADR-012 — Extension schéma annotation v3.0.1b : données contact fournisseur

**Date**       : 2026-03-15
**Statut**     : ACCEPTÉ
**Auteur**     : Abdoulaye Ousmane — CTO DMS
**Réf PR**     : #189
**Supérieur à**: ADR-011

---

## Contexte

Le framework annotation DMS v3.0.1a (FREEZE 2026-03-15) définit le bloc
`identifiants` dans le schéma JSON de pré-annotation Mistral.

Ce bloc capturait :
- `supplier_name_raw`
- `supplier_name_normalized`
- `supplier_identifier_raw` (NIF / RCCM)
- `case_id`, `supplier_id`, `lot_scope`, `zone_scope`

Les documents terrain Mali (offres techniques, offres financières, offres
combinées) contiennent systématiquement des données de contact fournisseur :
adresse postale, téléphone, email, forme juridique. Ces données sont absentes
du schéma v3.0.1a et ne sont donc ni extraites par Mistral ni annotées
dans Label Studio.

---

## Décision

Bump du schéma vers **v3.0.1b** avec ajout de 4 champs dans `identifiants` :

| Champ | Type | Valeur par défaut |
|-------|------|-------------------|
| `supplier_legal_form` | string / ABSENT / NOT_APPLICABLE | `ABSENT` |
| `supplier_address_raw` | string brut / ABSENT / NOT_APPLICABLE | `ABSENT` |
| `supplier_phone_raw` | string brut / ABSENT | `ABSENT` |
| `supplier_email_raw` | string brut / ABSENT | `ABSENT` |

Ces champs suivent la NULL Doctrine v3.0.1a :
- `ABSENT` si le document est une offre mais le champ non trouvé
- `NOT_APPLICABLE` si document_role = source_rules

---

## Justification AXIOME-2

AXIOME-2 : *Un champ n'existe que s'il sert à classer, gater, scorer,
mémoriser ou profiler.*

Ces 4 champs servent à **enrichir le profil fournisseur** (table `vendors`,
Couche B). C'est explicitement dans le scope DMS. Ils apparaissent dans
les familles B (technical_offer) et C (financial_offer / combined_offer)
ciblées par M12.

---

## Périmètre du changement

```
MODIFIÉ  : services/annotation-backend/backend.py
             SCHEMA_VERSION    = "v3.0.1b"
             FRAMEWORK_VERSION = "annotation-framework-v3.0.1b"
             FALLBACK_RESPONSE.identifiants += 4 champs (constante ABSENT)
             PROMPT_SYSTEM += règle 11 extraction contact
             _build_prompt identifiants += 4 champs

MODIFIÉ  : Label Studio XML (Dashboard)
             Bloc META : M.3 supplier_legal_form (Choices)
                         M.5 supplier_address_raw (TextArea)
                         M.6 supplier_phone_raw (TextArea)
                         M.7 supplier_email_raw (TextArea)
             Numérotation M.1 → M.11

CRÉÉ     : docs/adr/ADR-012_schema_v3.0.1b_supplier_contact.md

NON MODIFIÉ : docs/freeze/ANNOTATION_FRAMEWORK_DMS_v3.0.1.md
              Ce fichier est FREEZE ABSOLU (RÈGLE-ANCHOR-05).
              Le schéma v3.0.1b est un ADDENDUM — pas une révision du freeze.
```

---

## Compatibilité

- Additive uniquement — aucun champ supprimé
- Rétrocompatible : les annotations v3.0.1a restent valides
- Les 4 nouveaux champs sont optionnels dans la validation DONE binaire
  (leur absence = ABSENT acceptable)
- Applicable immédiatement M12 — pas de migration DB requise

---

## Sécurité

`supplier_phone_raw` et `supplier_email_raw` sont des données potentiellement
sensibles. Règles appliquées :

1. `_parse_mistral_response` : log safe uniquement (len + hash SHA256[:12])
   Zéro contenu raw en logs — même pattern que `safe_log_parse_failure`
   dans `src/couche_b/imc_map.py` (PR #188).
2. Ces champs ne sont jamais loggués en clair.
3. Ils transitent uniquement en mémoire vers Label Studio (R-05).

---

## Gouvernance

Modification additive — GO CTO explicite (2026-03-15).
Conforme RÈGLE ANCHOR-10 et Framework v3.0.1a Partie XVII :
*"Évolution future : additive uniquement. GO CTO obligatoire."*

Prochaine révision majeure du framework → v3.1.0 (hors scope M12).
