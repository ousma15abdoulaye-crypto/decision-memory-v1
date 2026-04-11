# M13 — Politique de rétention et cycle de vie (`m13_regulatory_profile_versions`)

## Principe

- Les lignes sont **append-only** : chaque run M13 qui persiste crée une **nouvelle** `version` pour le même `case_id` (pas d’UPDATE destructif du dernier profil).
- La vérité « courante » pour un dossier est la ligne avec **`version` maximale** pour ce `case_id`.

## Lecture

- Utiliser `M13RegulatoryProfileRepository.get_latest(case_id)` pour récupérer le `payload` JSONB de cette dernière version, ou `None` si absent / erreur (log côté repository).

## Rétention et purge

- **Pas de purge automatique** dans le code applicatif sans mandat ops explicite.
- Toute rétention (durée, archivage, anonymisation) est une **décision organisationnelle** (RGPD, audit) et doit être documentée dans un runbook ops séparé si elle est activée.

## Contenu dégradé

- Un profil avec `procedure_type` ou cadre peu résolu peut être persisté ; le caractère dégradé doit être **visible** dans `m13` / `profile_index` (pas d’échec silencieux du pipeline pour ce seul motif — voir mandat produit).

## Surveillance

- Alerter sur échecs répétés de `save_payload` / RLS (logs `m13_regulatory_profile`).
- Requêtes d’audit : compter les versions par `case_id`, dernière `persisted_at` dans le payload.
