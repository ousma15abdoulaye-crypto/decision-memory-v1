# PR — ADR-0007 Freeze + M-EXTRACTION-CORRECTIONS (#4)

## Lot A — Preuves (OBLIGATOIRE)

### A0.0 — Pattern migrations Alembic
```
0XX style dominant (002 → 014). Hash caf949970819 pour merge.
→ Nouvelle migration : 015_m_extraction_corrections
```

### A0.1 — Dernière révision réelle
```
Head : 014_ensure_extraction_tables
down_revision : 014_ensure_extraction_tables
```

### A0.2 — Chemins imports
- `get_db_cursor` : **src/db/connection.py** (l.18)
- `get_current_user` : **src/auth.py** (l.104)

### A0.3 — Extensions DB
- pgcrypto : utilisé dans 012, CI. **Autorisé.**

### A0.4 — Triggers sur extractions
- Aucun dans migrations 002–014. Trigger FSM uniquement sur extraction_jobs.

### A0.5 — UPDATE extractions dans le code
- **Vide** (0 match). Trigger immuabilité extractions activé.

### A0.6 — Fichier routes
- `src/api/routes/extractions.py` — 255 lignes (< 400). Endpoints ajoutés dedans.

---

## Lot B — Livrables

- [x] Migration **015_m_extraction_corrections** (table, vues, triggers)
- [x] Endpoints dans `extractions.py` : `/effective`, `POST /corrections`, `GET /corrections/history`
- [x] `main.py` : `include_router(extraction_router)`
- [x] Fixtures : `extraction_correction_fixture` (conftest racine + db_integrity)
- [x] Tests : retrait des `skip`, 6 tests actifs
- [x] ruff + black — OK

---

## Plan arrêt CI rouge (B4.1)

- Si CI rouge après push → 1ère correction.
- Si CI rouge encore après 2 tentatives → **STOP**. Pas de merge. Pas de `.done`.
- Poster commentaire PR avec log + diagnostic.

---

## .done

- **Interdit** tant que CI n'est pas verte.
- Créer `.milestones/M-EXTRACTION-CORRECTIONS.done` en dernier après merge.
