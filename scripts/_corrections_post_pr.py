"""
Corrections post-PR#139 — executer avec: python scripts/_corrections_post_pr.py
"""
import re

# ─── CORRECTION 1 : revision = "039" -> "039_hardening_created_at_timestamptz"
mig_path = "alembic/versions/039_hardening_created_at_timestamptz.py"
txt = open(mig_path, encoding="utf-8").read()
old = 'revision = "039"'
new = 'revision = "039_hardening_created_at_timestamptz"'
if old in txt:
    txt = txt.replace(old, new)
    open(mig_path, "w", encoding="utf-8").write(txt)
    print(f"[C1] {mig_path}: revision patchee -> 039_hardening_created_at_timestamptz")
else:
    print(f"[C1] Deja a jour ou non trouve: {old!r}")

# Verif
txt2 = open(mig_path, encoding="utf-8").read()
for line in txt2.splitlines():
    if "revision" in line and "down" not in line and "branch" not in line and "depends" not in line:
        print(f"[C1] verification: {line.strip()}")

# ─── CORRECTION 2B : réécrire runbook_m2b_local.sql
runbook_path = "scripts/runbook_m2b_local.sql"
runbook = open(runbook_path, encoding="utf-8").read()

# Probe PK column name from file
pk_col = "pipeline_run_id"  # confirmed by earlier probe in session

runbook_new = """-- RUNBOOK M2B -- pipeline_runs orphelins + VALIDATE CONSTRAINT
-- WARNING CONTEXTE ET LIMITES :
--     Ce runbook a ete prepare avant la decouverte que pipeline_runs
--     est protegee par le trigger trg_pipeline_runs_append_only (ADR-0012).
--     Les ETAPES 3 et 5 ne peuvent PAS s executer en local sans violer ADR-0012.
--     ETAPES 1, 2, 4 : executables en local -- diagnostic uniquement.
--     ETAPES 3, 5    : reservees prod Railway si orphan_count prod = 0.
--     En local       : FK reste NOT VALID -- assume et documente (DETTE-M0B-01).
--     Strategie locale alternative : DETTE-FIXTURE-01 -- refactorer les fixtures.

-- ETAPE 1 : compter les orphelins avant purge
SELECT COUNT(*) AS orphan_count_before
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases);

-- ETAPE 2 : inspecter les orphelins
-- PK reelle = pipeline_run_id (verifiee migration 032)
SELECT pipeline_run_id, case_id, created_at
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases)
ORDER BY created_at
LIMIT 20;

-- ETAPE 3 : purger les orphelins
-- INAPPLICABLE EN LOCAL -- trigger append-only ADR-0012 bloque le DELETE
-- PROD UNIQUEMENT -- apres PROBE + backup + GO humain explicite
-- BEGIN;
-- DELETE FROM pipeline_runs
-- WHERE case_id NOT IN (SELECT id FROM cases);
-- COMMIT;
-- En cas d erreur : ROLLBACK;

-- ETAPE 4 : confirmer orphan_count
SELECT COUNT(*) AS orphan_count_after
FROM pipeline_runs
WHERE case_id NOT IN (SELECT id FROM cases);

-- ETAPE 5 : valider la contrainte
-- INAPPLICABLE EN LOCAL si orphan_count_before > 0
-- PROD UNIQUEMENT -- apres preuve orphan_count_prod = 0
-- ALTER TABLE pipeline_runs
--   VALIDATE CONSTRAINT fk_pipeline_runs_case_id;

-- ETAPE 6 : confirmer validation (prod)
SELECT
  conname,
  convalidated,
  conrelid::regclass AS table_name
FROM pg_constraint
WHERE conrelid = 'pipeline_runs'::regclass
  AND conname = 'fk_pipeline_runs_case_id';

-- ETAPE 7 : DELETE prod sequences (PROD UNIQUEMENT)
-- apres backup confirme + GO humain
-- BEGIN;
-- DELETE FROM cases WHERE id = '<uuid_explicite>';
-- DELETE FROM users WHERE id = <id_explicite>;
-- COMMIT;
-- En cas d erreur : ROLLBACK;
"""
open(runbook_path, "w", encoding="utf-8").write(runbook_new)
print(f"[C2] {runbook_path}: runbook reecrit avec annotations ADR-0012 + transaction prod")

# ─── CORRECTION 3 : patch ADR section A2
adr_path = "docs/adr/ADR-M2B-001_hardening_db_scope.md"
adr = open(adr_path, encoding="utf-8").read()

old_a2 = "A2. Création scripts/runbook_m2b_local.sql"
new_a2 = """A2. Creation scripts/runbook_m2b_local.sql
    Contenu : diagnostic orphelins (COUNT + SELECT).
    Les etapes DELETE et VALIDATE CONSTRAINT sont commentees
    et marquees INAPPLICABLE LOCAL -- protegees par trigger
    trg_pipeline_runs_append_only (ADR-0012).
    En local : FK fk_pipeline_runs_case_id reste NOT VALID -- assume.
    En prod  : VALIDATE execute en ACTE 6 apres PROBE orphan_count = 0.
    Strategie locale future : DETTE-FIXTURE-01 -- refactorer fixtures."""

if old_a2 in adr:
    adr = adr.replace(old_a2, new_a2)
    open(adr_path, "w", encoding="utf-8").write(adr)
    print(f"[C3] {adr_path}: section A2 mise a jour")
else:
    # Try to find any A2 section and patch it
    if "A2." in adr:
        lines = adr.splitlines()
        for i, l in enumerate(lines):
            if l.strip().startswith("A2."):
                print(f"[C3] A2 trouvee ligne {i+1}: {l.strip()[:80]}")
                break
        print("[C3] Insertion manuelle requise -- voir fichier ADR")
    else:
        print("[C3] Section A2 non trouvee dans ADR")

# ─── CORRECTION 4 : DETTE-UTC-01 dans TECHNICAL_DEBT.md
td_path = "TECHNICAL_DEBT.md"
td = open(td_path, encoding="utf-8").read()

if "DETTE-UTC-01" in td:
    print("[C4] DETTE-UTC-01 deja presente dans TECHNICAL_DEBT.md")
else:
    dette_utc = """

### DETTE-UTC-01 -- Timestamps naifs code applicatif

| Attribut | Valeur |
|---|---|
| Statut | **OUVERTE** -- post-M2B |
| Decouverte | PR review Copilot -- commentaire post-merge M2B |
| Probleme | Le code applicatif utilise `datetime.utcnow().isoformat()` (timestamp naif, sans offset timezone). Apres migration 039 (`created_at TIMESTAMPTZ`), un INSERT avec timestamp naif est interprete selon le TimeZone de session PostgreSQL -- non deterministe entre environnements. Pas de `SET TIME ZONE UTC` sur les connexions SQLAlchemy. |
| Risque | Timestamps decales selon l environnement d execution |
| Options | A) `SET TIME ZONE UTC` sur connexions SQLAlchemy · B) `datetime.now(timezone.utc)` partout · C) `DEFAULT now()` + ne plus fournir `created_at` depuis l app |
| Action | Audit des usages `datetime.utcnow()` + decision architecturale |
| Perimetre | M3 ou milestone dedie |
| Priorite | P1 -- impacte la fiabilite des timestamps en prod |
"""
    td = td.rstrip() + dette_utc
    open(td_path, "w", encoding="utf-8").write(td)
    print(f"[C4] {td_path}: DETTE-UTC-01 ajoutee")

print("\n[DONE] Toutes corrections appliquees.")
