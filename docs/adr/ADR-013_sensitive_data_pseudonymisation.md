# ADR-013 — Pseudonymisation données sensibles annotation v3.0.1b

**Date**   : 2026-03-15
**Statut** : ACCEPTÉ
**Auteur** : Abdoulaye Ousmane — CTO DMS
**Réf**    : Post PR #189 — données sensibles annotation

---

## Contexte

Le schéma v3.0.1b introduit l'extraction de données contact fournisseur :
`supplier_phone_raw`, `supplier_email_raw`, `supplier_address_raw`.

Le framework v3.0.1a capturait déjà `has_rib`, `has_nif`, `has_rccm`
comme booléens. Ces champs vérifient la PRÉSENCE de documents sensibles
mais n'extraient pas leur valeur brute.

Problème identifié : sans règle explicite, Mistral pourrait extraire
la valeur brute du RIB (IBAN + clé), du NIF, du RCCM dans le JSON
de pré-annotation, les exposant dans Label Studio et les logs.

---

## Décision

### Règle 1 — RIB / NIF / RCCM : booléen uniquement

Le prompt Mistral demande UNIQUEMENT :
  `has_rib`  = true / false / ABSENT
  `has_nif`  = true / false / ABSENT
  `has_rccm` = true / false / ABSENT

La valeur brute (numéro IBAN, numéro NIF, numéro RCCM) n'est
JAMAIS demandée au modèle. Elle n'apparaît jamais dans extracted_json.

### Règle 2 — Phone / Email : pseudonymisation par hash salé

`supplier_phone_raw` et `supplier_email_raw` sont pseudonymisés
avant insertion dans extracted_json :

```
pseudo = HMAC-SHA256(valeur_brute, sel=PSEUDONYM_SALT)[:16]
```

Le JSON Label Studio contient :
```json
{
  "supplier_phone_pseudo": "a3f9c2b1d4e87654",
  "supplier_phone_present": true
}
```

Jamais la valeur brute en clair.

### Règle 3 — Address : conservée tronquée

`supplier_address_raw` est conservée mais tronquée à 60 caractères.
Elle est nécessaire pour le matching zone géographique Couche B.
Elle ne contient pas de données bancaires.

### Règle 4 — Sel projet

`PSEUDONYM_SALT` = variable d'environnement obligatoire.
Si absente → WARNING + fallback SHA256 sans sel (dégradé acceptable).
Jamais hardcodé dans le code.

---

## Ce qui NE change PAS

- `has_rib` / `has_nif` / `has_rccm` = booléens — inchangés
- `supplier_name_raw` = texte conservé (nécessaire matching vendor)
- `supplier_legal_form` = texte conservé (non sensible)
- `supplier_address_raw` = tronqué 60 chars

---

## Compatibilité

Additive — pas de migration DB.
Les annotations v3.0.1b existantes avec phone/email en clair
doivent être re-annotées (volume = 0 à ce stade M12 day-1).

---

## Références

- RÈGLE-15 : Documents réels raw_received jamais committés
- RÈGLE-19 : value + confidence + evidence
- E-30 : log safe phone/email
- donneespersonnelles.fr : pseudonymisation vs anonymisation
- lemeilleurannuaire.fr : hachage + salage — stockage séparé obligatoire
