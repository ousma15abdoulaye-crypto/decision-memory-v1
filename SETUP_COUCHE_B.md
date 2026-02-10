# Couche B Setup Guide

## Quick Start

The repository has been restructured for Constitution V2.1 implementation. All skeleton files are in place with TODO markers for the Cursor agent to implement.

### Structure Created

```
src/couche_b/           - Market Intelligence Layer
tests/couche_b/         - Test suite
scripts/                - Utility scripts
alembic/                - Database migrations
docs/                   - API documentation
```

### Next Steps

#### Option 1: Cursor Agent (Recommended)
Open the project in Cursor and follow `CURSOR_AGENT_INSTRUCTIONS.md` for the 6-session implementation plan.

```bash
cursor .
# Then follow CURSOR_AGENT_INSTRUCTIONS.md
```

#### Option 2: Manual Setup

1. **Install Dependencies**
```bash
pip install -r requirements_v2.txt
```

2. **Initialize Database**
```bash
python -c "from src.db import init_db; init_db()"
```

3. **Run Alembic Migrations**
```bash
alembic revision --autogenerate -m "Initial Couche B schema"
alembic upgrade head
```

4. **Seed Data**
```bash
python scripts/seed_production.py
```

5. **Run Tests**
```bash
pytest tests/couche_b/ -v
```

### Validation

Check structure is complete:
```bash
./scripts/check_structure.sh
```

Validate alignment with Constitution:
```bash
python scripts/validate_alignment.py
```

### Implementation Sessions

See `CURSOR_AGENT_INSTRUCTIONS.md` for the detailed 6-session plan:

1. **Session 1**: Database Schema (10 tables)
2. **Session 2**: Resolvers & Seed Data
3. **Session 3**: API Endpoints (Catalog + Survey)
4. **Session 4**: Market Intelligence
5. **Session 5**: Testing & Validation
6. **Session 6**: Documentation & Polish

### Key Files

- `.cursorrules` - Agent execution rules
- `CURSOR_AGENT_INSTRUCTIONS.md` - Implementation plan
- `docs/constitution_v2.1.md` - Technical specification
- `docs/API_COUCHE_B.md` - API documentation
- `docs/RESOLVERS_GUIDE.md` - Resolver documentation

### TODO Implementation

All files contain TODO markers indicating what needs to be implemented:

- `# TODO Session 1.2: Implémenter 9 tables` - In `src/couche_b/models.py`
- `# TODO Session 2.1: Implémenter resolvers` - In `src/couche_b/resolvers.py`
- `# TODO Session 2.2: Implémenter seed` - In `src/couche_b/seed.py`
- `# TODO Session 3.1: Implémenter endpoints` - In `src/couche_b/routers.py`

### Dependencies

New dependencies for Couche B (in `requirements_v2.txt`):

- SQLAlchemy 2.0.27 (async database)
- Alembic 1.13.1 (migrations)
- asyncpg 0.29.0 (PostgreSQL async driver)
- fuzzywuzzy 0.18.0 (entity matching)
- python-Levenshtein 0.25.0 (string similarity)

### Support

- Constitution V2.1: `docs/constitution_v2.1.md`
- API Spec: `docs/API_COUCHE_B.md`
- Resolver Spec: `docs/RESOLVERS_GUIDE.md`

---

**Status**: ✅ Structure Complete - Ready for Implementation
