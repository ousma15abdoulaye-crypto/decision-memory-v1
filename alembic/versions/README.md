# Alembic Migrations — Decision Memory System

## 🔗 Migration Chain

```
None
  ↓
002_add_couche_a (2026-02-11)
  └─ Tables Couche B : cases, artifacts, memory_entries, dao_criteria, cba_template_schemas, offer_extractions
  └─ Tables Couche A : lots, offers, documents, extractions, analyses, audits
  ↓
003_add_procurement_extensions (2026-02-12) — M2-Extended
  └─ Tables : procurement_references, procurement_categories, purchase_categories, procurement_thresholds
  └─ Colonnes cases : ref_id, category_id, purchase_category_id, estimated_value, closing_date, procedure_type
  └─ Colonnes lots : category_id
  └─ Seed : 6 procurement_categories + 9 purchase_categories (Manuel SCI) + 3 thresholds
  ↓
004_users_rbac (2026-02-12) — M4A-F (Auth + RBAC)
  └─ Tables : users, roles, permissions, role_permissions
  └─ Colonnes cases : owner_id, total_upload_size
  └─ Colonnes artifacts : created_by
  └─ Seed : 3 roles (admin, procurement_officer, viewer) + 1 admin user
```

## 📋 Current Schema Version (Production)

**Expected**: `004_users_rbac`

Check with:
```bash
psql $DATABASE_URL -c "SELECT version_num FROM alembic_version"
```

## 🚀 Initial Setup (Fresh Database)

```bash
# 1. Set DATABASE_URL
export DATABASE_URL="postgresql+psycopg://user:password@host:5432/dbname"

# 2. Run migrations
alembic upgrade head

# 3. Verify
alembic current
# Should show: 004_users_rbac (head)

# 4. Start app
python main.py
# Or: uvicorn main:app --host 0.0.0.0 --port 5000
```

## 🔄 Applying New Migrations

```bash
# Pull latest code
git pull origin main

# Check pending migrations
alembic current
alembic history

# Apply migrations
alembic upgrade head

# Rollback (if needed)
alembic downgrade -1       # Rollback one migration
alembic downgrade 002_add_couche_a  # Rollback to specific version
```

## 🧪 Testing Migrations Locally

```bash
# Use test database
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/test_dms"

# Fresh install
dropdb test_dms && createdb test_dms
alembic upgrade head

# Test downgrade/upgrade cycle
alembic downgrade base
alembic upgrade head
```

## ⚠️ Important Notes

### Constitution V2.1 Compliance
- ❌ **NEVER** use `metadata.create_all()` or manual table creation
- ✅ **ALWAYS** use Alembic migrations for schema changes
- ✅ All migrations must use `IF NOT EXISTS` / `IF EXISTS` for idempotency
- ✅ Migrations must handle both `Engine` (tests) and `Connection` (Alembic CLI)

### Migration Best Practices
1. **Test locally** before pushing
2. **Idempotent operations** : Use `IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`
3. **Data migrations** : Separate DDL and DML (use separate migrations if needed)
4. **Rollback support** : Always implement `downgrade()`
5. **Foreign keys** : Use `ondelete='CASCADE'` for cleanup

### Seed Data
Migrations include seed data for:
- **003**: Procurement categories (6 + 9 from Manuel SCI) + thresholds (3)
- **004**: Roles (3) + admin user (username: `admin`, password: `Admin123!`)

### Breaking Changes
- ❌ Don't modify existing migrations (create new ones)
- ❌ Don't delete old migrations (Git history must remain intact)
- ✅ Add new migration for schema changes
- ✅ Document breaking changes in migration docstring

## 🐛 Troubleshooting

### "alembic_version table not found"
```bash
# Initialize Alembic version table
alembic stamp head
```

### "target database is not up to date"
```bash
# Check current version
alembic current

# See pending migrations
alembic history

# Apply missing migrations
alembic upgrade head
```

### Migration fails with "relation already exists"
This should NOT happen if migrations use `IF NOT EXISTS`. If it does:
```bash
# Check actual DB state
psql $DATABASE_URL -c "\dt"

# Manually stamp to correct version (DANGER: only if you know what you're doing)
alembic stamp 004_users_rbac
```

### Rollback to known good state
```bash
# Downgrade to 002 (before M2-Extended)
alembic downgrade 002_add_couche_a

# Reapply
alembic upgrade head
```

## 📚 References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [DMS Constitution V2.1](../CONSTITUTION.md)
- [Audit Report](../AUDIT_REPORT.md)
