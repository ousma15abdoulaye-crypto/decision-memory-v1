# Vendor Import — Guide opérateur

<!-- Ref : incident 2026-04-03/04 · 661 vendors en échec · mismatch schéma -->
<!-- Maintenu par : équipe DMS · mise à jour obligatoire après chaque migration vendors -->

## Contexte

661 vendors ont échoué à l'insertion en base les 3-4 avril 2026 à cause d'un mismatch
entre le code d'import et le schéma actuel. Les erreurs observées dans les logs DB :

```
null value in column "vendor_id"
null value in column "region_code"
null value in column "canonical_name"
invalid input value for enum: "activity_status"
```

**Cause racine** : du code ou des requêtes SQL manuelles utilisaient les anciens noms de
colonnes de `vendor_identities` (avant migrations 041-043 et `m5_pre_vendors_consolidation`).
La table a été renommée en `vendors` et les colonnes ont évolué.

**Résolution** : `etl_vendors_m4.py` intègre désormais des vérifications pré-import
(`run_preflight_checks()`) qui bloquent l'import avec un message explicite si le schéma
ne correspond pas.

### Clarification des chiffres (661 vs 103) — cible « completeness »

| Métrique | Ce que c’est | Ce que ce n’est **pas** |
|----------|----------------|-------------------------|
| **661** (incident 3–4 avr. 2026) | Volume **d’échecs d’insertion** observés dans les logs (mismatch schéma / contraintes) lors d’une ou plusieurs passes d’import. | **Ni** un objectif métier « il doit y avoir 661 fournisseurs en base », **ni** la taille d’un référentiel national à atteindre par ce seul script. |
| **103** (ETL M4, deux fichiers Excel listés dans `FILES`) | **Lot attendu** pour ce périmètre : lignes données présentes dans les sources versionnées (ex. 50 + 53 lignes → **103 lignes lues** lorsque les xlsx sont complets). C’est le **chiffre cible du lot M4** tel que défini dans le code. | Un sous-ensemble arbitraire « des 661 » : **661 et 103 ne sont pas le même dénominateur** (incident vs périmètre fichier). |

**Complétude référentiel vendors (hors seul M4)** : d’autres lots ou scripts peuvent viser d’autres fichiers (ex. `scripts/etl_vendors_wave2.py` et `SUPPLIER DATA Mali FINAL.xlsx`). Tant qu’une **décision produit** n’a pas fixé un volume unique « national » et les sources associées, la dette **« vendors completeness »** au sens couverture métier reste **ouverte** — alors que le **lot M4** peut être considéré **complet** lorsque l’ETL lit bien toutes les lignes des fichiers `FILES` sans rejet systémique.

---

## Schéma actuel (migration 043 + m4_patch_a + m5_pre_vendors_consolidation)

**Table** : `vendors` (renommée depuis `vendor_identities` via `m5_pre_vendors_consolidation`)

**Migration courante** : 067 (`fix_market_coverage_trigger`)

### Colonnes obligatoires pour l'import

| Colonne              | Type        | Nullable | Default  | Source                          |
|----------------------|-------------|----------|----------|---------------------------------|
| `vendor_id`          | TEXT UNIQUE | NO       | —        | `repository.build_vendor_id()`  |
| `fingerprint`        | TEXT UNIQUE | NO       | —        | `repository.generate_fingerprint()` |
| `name_raw`           | TEXT        | NO       | —        | Excel source                    |
| `name_normalized`    | TEXT        | NO       | —        | `normalizer.normalize_text()`   |
| `canonical_name`     | TEXT UNIQUE | NO       | —        | `name_normalized\|region_code`  |
| `zone_raw`           | TEXT        | YES      | NULL     | Excel source                    |
| `zone_normalized`    | TEXT        | YES      | NULL     | `normalizer.normalize_zone()`   |
| `region_code`        | TEXT        | NO       | —        | `region_codes.ZONE_TO_REGION`   |
| `category_raw`       | TEXT        | YES      | NULL     | Excel source                    |
| `email`              | TEXT        | YES      | NULL     | `normalizer.normalize_email()`  |
| `phone`              | TEXT        | YES      | NULL     | `normalizer.normalize_phone()`  |
| `email_verified`     | BOOLEAN     | NO       | FALSE    | `bool(email)`                   |
| `activity_status`    | TEXT        | NO       | UNVERIFIED | Voir valeurs valides ci-dessous |
| `verified_by`        | TEXT        | YES      | NULL     | Ex. `SCI_FIELD_TEAM_MALI`       |
| `verification_source`| TEXT        | YES      | NULL     | Ex. `SCI_FIELD_VISIT`           |
| `is_active`          | BOOLEAN     | NO       | TRUE     | Toujours TRUE à l'import        |
| `source`             | TEXT        | NO       | MANUAL   | Ex. `EXCEL_M4`                  |

### Valeurs valides pour `activity_status`

```
VERIFIED_ACTIVE   — Fournisseur vérifié actif (visite terrain SCI)
UNVERIFIED        — Statut par défaut · non vérifié
INACTIVE          — Inactif · plus en activité
GHOST_SUSPECTED   — Suspicion d'entité fantôme
```

Contrainte DB : `chk_activity_status` sur la table `vendors`.

### Valeurs valides pour `verification_source`

```
SCI_FIELD_VISIT       — Visite terrain SCI
PHONE_CONFIRMATION    — Confirmation téléphonique
DOCUMENT_REVIEW       — Revue documentaire
LEGACY_IMPORT         — Import historique
MANUAL_ENTRY          — Saisie manuelle
```

---

## Historique des migrations vendors

| Migration                          | Changement                                              |
|------------------------------------|---------------------------------------------------------|
| `041_vendor_identities`            | Création table `vendor_identities`                      |
| `042_vendor_fixes`                 | Regex CHECK sur `vendor_id`, fix trigger                |
| `043_vendor_activity_badge`        | Ajout `activity_status`, `verified_by`, `verification_source` |
| `m4_patch_a_vendor_structure_v410` | Ajout `canonical_name`, `verification_status`, `vcrn`, etc. |
| `m5_pre_vendors_consolidation`     | **RENAME** `vendor_identities` → `vendors`              |
| `048_vendors_sensitive_data`       | Tables annexes `vendors_sensitive_data`, `vendors_doc_validity` |
| `072_vendor_market_signals_watchlist` | Tables `vendor_market_signals`, `market_watchlist_items` |

---

## Lancer l'import

### Prérequis

```bash
# Variables d'environnement
export DATABASE_URL="postgresql://..."

# Fichiers source (placer dans data/imports/m4/)
#   Supplier DATA BAMAKO.xlsx
#   Supplier DATA Mopti et autres zones nords.xlsx
```

### Dry-run (recommandé avant tout import réel)

```bash
python scripts/etl_vendors_m4.py --dry-run
```

Le dry-run effectue les vérifications pré-import complètes, normalise toutes les lignes,
et rapporte ce qui serait importé — sans aucun INSERT en base.

### Import réel

```bash
python scripts/etl_vendors_m4.py
```

L'import effectue automatiquement les vérifications pré-import (`run_preflight_checks()`)
avant le premier INSERT. Si le schéma ne correspond pas, l'import est bloqué avec un
message explicite indiquant la migration manquante.

### Vérification compatibilité après migration

```bash
python scripts/etl_vendors_m4.py --check-migration-compat
```

À utiliser après le déploiement de nouvelles migrations touchant `vendors` (ex. 078/079).
Détecte les nouvelles colonnes NOT NULL sans DEFAULT qui casseraient les INSERTs existants.

---

## Codes d'erreur pré-import

| Code              | Cause                                              | Correction                                    |
|-------------------|----------------------------------------------------|-----------------------------------------------|
| `STOP-PREFLIGHT-1`| Table `vendors` introuvable                        | `alembic upgrade head`                        |
| `STOP-PREFLIGHT-2`| Colonnes manquantes (ex. `canonical_name`)         | `alembic upgrade head` · vérifier 041-043     |
| `STOP-PREFLIGHT-3`| Contrainte `chk_activity_status` absente/modifiée  | `alembic upgrade head` · vérifier 043         |
| `STOP-PREFLIGHT-4`| Colonnes NOT NULL obligatoires absentes            | `alembic upgrade head`                        |
| `STOP-COMPAT-1`   | Nouvelle colonne NOT NULL sans DEFAULT (078/079)   | Mettre à jour `repository.py` + `REQUIRED_COLUMNS` |
| `STOP-M4-G`       | Taux de rejet > 15% (zones inconnues)              | Vérifier `ZONE_TO_REGION` dans `region_codes.py` |

---

## Procédure après déploiement migrations 078/079

**CRITIQUE** : effectuer ces étapes AVANT de relancer l'import si 078/079 ont été déployées.

1. **Vérifier la compatibilité** :
   ```bash
   python scripts/etl_vendors_m4.py --check-migration-compat
   ```

2. **Si `STOP-COMPAT-1`** (nouvelle colonne NOT NULL sans DEFAULT) :
   - Lire la migration 078 ou 079 pour identifier la nouvelle colonne
   - Ajouter la colonne à `REQUIRED_COLUMNS` dans `etl_vendors_m4.py`
   - Ajouter la colonne à `NOT_NULL_COLUMNS` si applicable
   - Mettre à jour `insert_vendor()` dans `src/vendors/repository.py`
   - Mettre à jour ce README (tableau "Colonnes obligatoires")
   - Relancer `--dry-run` pour valider

3. **Si `[WARN]` seulement** (nouvelle colonne nullable ou avec DEFAULT) :
   - L'import existant n'est pas cassé
   - Décider si la nouvelle colonne doit être peuplée à l'import
   - Si oui : mettre à jour `insert_vendor()` et ce README

4. **Si `[OK]`** : aucune action requise · relancer l'import normalement.

---

## Architecture — Séparation des responsabilités

```
etl_vendors_m4.py          → Lecture Excel · normalisation · orchestration
  └─ run_preflight_checks() → Validation schéma DB avant INSERT
  └─ run_etl()              → Boucle principale · appelle insert_vendor()
  └─ check_migration_compat() → Vérification post-migration

src/vendors/repository.py  → Accès DB · SQL paramétré · ADR-0003
  └─ insert_vendor()        → INSERT atomique · ON CONFLICT DO NOTHING
  └─ generate_fingerprint() → SHA-256 · anti-doublon déterministe
  └─ get_next_sequence()    → MAX()+1 · TD-001 · acceptable séquentiel

src/vendors/normalizer.py  → Normalisation texte · source de vérité unique
src/vendors/region_codes.py → ZONE_TO_REGION · build_vendor_id()
```

**Règle fondamentale** : `vendor_id` est généré dans `repository.insert_vendor()`,
jamais dans l'ETL. `canonical_name` est calculé comme `name_normalized|region_code`.

---

## Ajouter un nouveau fichier source

1. Ajouter l'entrée dans `FILES` dans `etl_vendors_m4.py`
2. Vérifier le mapping colonnes dans `COLUMN_MAP` (probe les en-têtes Excel)
3. Lancer `--dry-run` pour valider le taux de rejet
4. Si taux > 5% : vérifier `ZONE_TO_REGION` et ajouter les zones manquantes
5. Valider avec CTO avant import réel (règle scripts/README.md)

---

## Références

- `alembic/versions/041_vendor_identities.py` — Création initiale
- `alembic/versions/043_vendor_activity_badge.py` — Contrainte activity_status
- `alembic/versions/m4_patch_a_vendor_structure_v410.py` — canonical_name, verification_status
- `alembic/versions/m5_pre_vendors_consolidation.py` — Rename vendor_identities → vendors
- `src/vendors/repository.py` — insert_vendor() · source de vérité SQL
- `TECHNICAL_DEBT.md` — TD-001 (get_next_sequence non atomique)
- `ADR-0003` — psycopg pur · zéro ORM
