# 1. Ajouter fichier
git add migrations/versions/003_add_procurement_extensions.py

# 2. Commit
git commit -m "fix(migrations): correct 003 with PostgreSQL syntax + no premature FK

- Separate ALTER TABLE statements (PostgreSQL requirement)
- Remove users FK (table created in 004)
- Foreign keys added after columns exist
- Tested: import OK, alembic history clean"

# 3. Push
git push origin $(git branch --show-current)
