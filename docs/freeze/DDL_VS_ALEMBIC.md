# DDL freeze vs schéma Alembic (note E-82)

**Autorité** : `docs/freeze/DMS_V4.1.0_FREEZE.md` est **normatif** pour l’intention produit (entités, champs, règles métier).

**Réalité SQL** : les types, contraintes, index et évolutions successives sont **matérialisés** par la chaîne `alembic/versions/`. En cas de divergence entre un extrait DDL dans le freeze et une migration (ex. `cases.id` en `TEXT` vs `UUID` dans un passage du document figé), l’implémentation et les nouvelles migrations doivent suivre **Alembic** et le schéma effectif en base.

**Ne pas** réécrire le freeze pour chaque ajustement de type ; documenter les écarts connus dans les ADR ou migrations lorsque c’est critique pour l’audit.

**Références** : `docs/adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md`, `scripts/validate_mrd_state.py` (`_KNOWN_MIGRATION_CHAIN`).
