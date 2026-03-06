# MANDAT M7.3b + ADR — DÉPRÉCIATION LEGACY + RETOUR M7 RÉEL
## DMS V4.2.0 · Migration propre · ADR gravé · Retour plan V4.1.0

**Émetteur : Tech Lead / Systems Engineer**
**Destinataire : Agent Dev Cursor**
**Branche : `feat/m7-3b-deprecate-legacy`**
**Prérequis : M7.3 mergé · HEAD = `m7_3_dict_nerve_center` · pytest vert**

---

## PARTIE 0 — ADR-0016 · DÉCISION ARCHITECTURALE

> **Note canonique :** ADR-007 existe déjà (Freeze M-EXTRACTION-CORRECTIONS). Dernier ADR = ADR-0015.
> Ce mandat utilise **ADR-0016** pour le détour M7.2/M7.3.

```markdown
# ADR-0016 — Détour M7.2 / M7.3 et retour M7 réel

**Fichier     :** docs/adrs/ADR-0016_m7-detour-taxonomy-nerve-center.md
**Date        :** 2026
**Statut      :** ACCEPTÉ
**Décideur    :** Abdoulaye Ousmane (CTO)
**Rédigé par  :** Tech Lead / Systems Engineer

---

## Contexte

Le Plan Directeur V4.1.0 (référence FREEZE) définit M7 ainsi :

  M7 = enrichissement contrôlé
       collisions + proposals
       dictionnaire vivant depuis données réelles M5/M6

À l'issue de M6, le dictionnaire contenait :
  · 1 488 items ingérés depuis mercurials.item_canonical
  · 9 familles plates (procurement_dict_families)
  · family_id = 'equipements' sur 1 443 items (97%)
  · domain_id / family_l2_id / subfamily_id = NULL sur tous

M7 tel que prévu devait enrichir ce dictionnaire
via proposals + validation humaine.

---

## Problème identifié avant M7

Deux défauts structurels ont été détectés :

DÉFAUT-STRUCT-01 · Taxonomie insuffisante
  9 familles plates ne permettent pas :
  · Une défense devant un auditeur DGMP / USAID / BM
  · Un lien avec les seuils DGMP par type d'achat
  · Une distinction item_type (good / service / works)
  · Un signal marché M9 contextualisé par domaine
  Solution → M7.2 : taxonomie L1/L2/L3 enterprise grade
             15 domaines · 57 familles · 155 sous-familles

DÉFAUT-STRUCT-02 · Infrastructure manquante
  Le dictionnaire n'avait pas :
  · Hash chain / audit trail sur les modifications
  · Seuils DGMP accessibles programmatiquement
  · Conversions UOM ISO
  · quality_score calculé automatiquement
  · Lien item ↔ fournisseur
  Sans cette infrastructure, M7 enrichissement = données
  sans traçabilité = non défendable en audit.
  Solution → M7.3 : nerve center · 4 tables + 9 colonnes + triggers

---

## Décision

Accepter le détour M7.2 + M7.3 avant M7 enrichissement réel.

Raison : construire sur du sable = refaire deux fois.
Un dictionnaire enrichi sans taxonomie correcte
= 1 488 items dans 9 familles plates
= inutilisable pour M9 (signal marché par domaine)
= indéfendable pour M14 (évaluation par type d'achat)
= rejeté par un auditeur DGMP au premier contrôle.

---

## Conséquences

POSITIF :
  · Taxonomie L1/L2/L3 disponible pour classify_taxo.py
  · Infrastructure audit trail opérationnelle
  · Seuils DGMP dans dgmp_thresholds (non hardcodés)
  · quality_score calculé automatiquement
  · family_id legacy déprécié proprement (M7.3b)

NÉGATIF :
  · Délai de 3 jalons sur M7 enrichissement réel
  · Complexité accumulée (à maîtriser · pas à ignorer)
  · 1 488 items avec domain_id = NULL
    jusqu'à exécution de classify_taxo.py

---

## M7 RÉEL — CE QUI DOIT ÊTRE LIVRÉ MAINTENANT

Après M7.3b (ce mandat), le plan V4.1.0 reprend
exactement comme prévu :

  ÉTAPE 1 · classify_taxo.py
    Peuple taxo_proposals_v2
    3 niveaux : seed_exact · trgm · llm_mistral
    Output : proposals · status=pending/approved/flagged

  ÉTAPE 2 · Validation humaine AO
    Review taxo_proposals_v2 status=pending
    Familles CRITIQUE en priorité :
    CARB_LUB · ALIM_VIVRES · SANTE · VEHICULES_ENGINS
    human_validated = TRUE sur items validés

  ÉTAPE 3 · seed_apply_taxo.py
    Copie domain_id / family_l2_id / subfamily_id
    depuis taxo_proposals_v2 status=approved
    vers procurement_dict_items
    RÈGLE-M7-03 : backfill script · jamais dans migration

  ÉTAPE 4 · Validation finale
    KPI : résiduel DIVERS_NON_CLASSE ≤ 25%
    KPI : quality_score moyen > 60
    Tag : v4.2.0-m7-dict-vivant

---

## Règles gravées issues de ce détour

RÈGLE-DICT-01  family_id legacy = READ-ONLY après M7.3b
RÈGLE-DICT-02  domain_id/family_l2_id/subfamily_id = cibles M7.2
RÈGLE-DICT-03  taxo_proposals_v2 = table de passage
               LLM propose · AO valide · backfill script applique
RÈGLE-DICT-04  Jamais deux systèmes de familles actifs simultanément
               Legacy = lecture historique uniquement
               M7.2 = source de vérité operative

---

## Alternatives rejetées

ALT-01 · Enrichir directement sur les 9 familles plates
         Rejeté : non défendable DGMP · inutilisable M9

ALT-02 · Supprimer family_id legacy (DROP COLUMN)
         Rejeté : RÈGLE-T04 · données historiques perdues
         Dépréciation propre = conservé + bloqué en écriture

ALT-03 · Attendre un sprint dédié taxonomie
         Rejeté : M9 bloqué sans domaines corrects
         Coût différé > coût immédiat

---

*ADR-0016 · DMS V4.2.0 · Tech Lead · 2026*
```

---

## PARTIE 1 — RÈGLES ACTIVES

```text
RÈGLE-08      Probe avant migration
RÈGLE-12      op.execute("SQL brut") · zéro sa.text()
RÈGLE-17      Toute migration = 1 test minimum
RÈGLE-T04     Tables legacy conservées · jamais DROP
RÈGLE-DICT-01 family_id = READ-ONLY après M7.3b
RÈGLE-DICT-02 domain_id/family_l2_id/subfamily_id = cibles M7.2
RÈGLE-DICT-03 taxo_proposals_v2 = table de passage uniquement
RÈGLE-DICT-04 Jamais deux systèmes familles actifs simultanément
PIÈGE-09      down_revision = alembic heads réel · copié · jamais supposé
PIÈGE-M7-04   Trigger BEFORE + OLD sur INSERT → deux triggers séparés
```

---

## PARTIE 2 — SIGNAUX STOP

```text
STOP-01   git status non clean
STOP-02   alembic heads > 1 ligne
STOP-03   pytest rouge
STOP-L1   match_item() écrit family_id → adapter avant trigger
STOP-L2   autre code src/ écrit family_id → lister · adapter avant trigger
STOP-L3   triggers_actifs ≠ 2 après migration
STOP-ADR  ADR-0016 non committé avant migration
```

---

## TEMPS 0 — BASELINE

```bash
git status --short
alembic heads
pytest -q --tb=short 2>&1 | tail -5
```

**Poster 3 outputs. STOP si rouge.**

---

## TEMPS 1 — ADR-0016 · COMMIT AVANT MIGRATION

```bash
# Créer le fichier
mkdir -p docs/adrs
# Écrire ADR-0016 (contenu docs/adrs/ADR-0016_m7-detour-taxonomy-nerve-center.md)

git add docs/adrs/ADR-0016_m7-detour-taxonomy-nerve-center.md
git commit -m "docs(adr): ADR-0016 détour M7.2/M7.3 et retour M7 réel"
```

**Poster hash du commit. STOP-ADR si non committé.**

---

## TEMPS 2 — PROBE · STOP ABSOLU

```python
# scripts/probe_m7_3b.py
"""
Probe pré-migration M7.3b · RÈGLE-08.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/probe_m7_3b.py
"""
from __future__ import annotations
import os, sys
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("❌ DATABASE_URL manquante")


def run() -> None:
    print("=" * 65)
    print("PROBE M7.3b · PRÉ-MIGRATION LEGACY FAMILIES")
    print("=" * 65)

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:

        # L1 · HEAD Alembic réel → down_revision à copier
        print("\n--- L1_ALEMBIC_HEAD ---")
        r = conn.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        print(f"  HEAD : {r['version_num']}")
        print(f"  → Copier exactement dans down_revision")

        # L2 · Usage family_id actuel
        print("\n--- L2_FAMILY_ID_USAGE ---")
        r = conn.execute("""
            SELECT
                COUNT(*)                                       AS total,
                COUNT(*) FILTER (WHERE family_id IS NOT NULL)  AS avec,
                COUNT(*) FILTER (WHERE family_id IS NULL)      AS sans,
                COUNT(DISTINCT family_id)                      AS distinctes
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
        """).fetchone()
        print(f"  Total actifs     : {r['total']}")
        print(f"  Avec family_id   : {r['avec']}")
        print(f"  Sans family_id   : {r['sans']}")
        print(f"  Valeurs distinct : {r['distinctes']}")

        # L3 · Valeurs distinctes
        print("\n--- L3_FAMILY_ID_VALEURS ---")
        rows = conn.execute("""
            SELECT family_id, COUNT(*) AS n
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE AND family_id IS NOT NULL
            GROUP BY family_id ORDER BY n DESC
        """).fetchall()
        for r in rows:
            print(f"  {r['family_id']:<30} {r['n']}")

        # L4 · Triggers existants sur dict_items
        print("\n--- L4_TRIGGERS_EXISTANTS ---")
        rows = conn.execute("""
            SELECT trigger_name, event_manipulation, action_timing
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
            ORDER BY trigger_name
        """).fetchall()
        if not rows:
            print("  (aucun)")
        for r in rows:
            print(
                f"  {r['trigger_name']:<45} "
                f"{r['action_timing']} {r['event_manipulation']}"
            )

        # L5 · Colonne deprecated déjà présente ?
        print("\n--- L5_DEPRECATED_EXISTE ---")
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM information_schema.columns
            WHERE table_schema = 'couche_b'
              AND table_name   = 'procurement_dict_families'
              AND column_name  = 'deprecated'
        """).fetchone()
        print(f"  deprecated présente : {'OUI' if r['n'] > 0 else 'NON'}")

        # L6 · Vue legacy déjà présente ?
        print("\n--- L6_VUE_LEGACY ---")
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM information_schema.views
            WHERE table_schema = 'couche_b'
              AND table_name   = 'legacy_procurement_families'
        """).fetchone()
        print(f"  vue legacy présente : {'OUI' if r['n'] > 0 else 'NON'}")

        # L7 · match_item() en DB ?
        print("\n--- L7_MATCH_ITEM_DB ---")
        rows = conn.execute("""
            SELECT routine_schema, routine_name
            FROM information_schema.routines
            WHERE routine_name ILIKE '%match%item%'
               OR routine_name ILIKE '%item%match%'
            ORDER BY 1, 2
        """).fetchall()
        if not rows:
            print("  (aucune fonction match_item en DB)")
        for r in rows:
            print(f"  {r['routine_schema']}.{r['routine_name']}")

    print("\n--- L8_USAGE_FAMILY_ID_CODE ---")
    print("  Commande à exécuter séparément :")
    print(
        "  grep -rn \"family_id\" src/ "
        "--include='*.py' | grep -v '#'"
    )
    print("\n" + "=" * 65)
    print("POSTER L1→L7 + grep L8 · STOP · GO TECH LEAD")
    print("=" * 65)


if __name__ == "__main__":
    run()
```

```bash
python scripts/probe_m7_3b.py
grep -rn "family_id" src/ --include="*.py" | grep -v "#"
```

**Poster L1→L7 + grep L8. STOP absolu.**

```text
SI grep L8 révèle des UPDATE/INSERT avec family_id dans src/ :
  → STOP-L2 · lister les fichiers · attendre GO Tech Lead
  → Adapter le code AVANT de créer le trigger

SI match_item() écrit family_id (L7 ou L8) :
  → STOP-L1 · adapter match_item() avant migration
```

---

## TEMPS 3 — MIGRATION · GO TECH LEAD REQUIS

> `down_revision` = valeur exacte L1. Copier. Coller. Jamais supposer.

```python
# alembic/versions/m7_3b_deprecate_legacy_families.py
"""
M7.3b · Dépréciation familles legacy M6.

DÉCISION : ADR-0016
  family_id = READ-ONLY historique après cette migration
  Nouvelles écritures → domain_id/family_l2_id/subfamily_id (M7.2)
  Tables legacy conservées (RÈGLE-T04) · jamais DROP

PIÈGE-M7-04 : deux triggers séparés INSERT / UPDATE
  OLD absent sur INSERT → trigger INSERT sans WHEN sur OLD
"""
from alembic import op

revision      = "m7_3b_deprecate_legacy_families"
down_revision = "<VALEUR_L1_DU_PROBE>"   # ← COPIER depuis L1
branch_labels = None
depends_on    = None


def upgrade() -> None:

    # 1 · Marquer procurement_dict_families comme deprecated
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_families
        ADD COLUMN IF NOT EXISTS deprecated
            BOOLEAN NOT NULL DEFAULT TRUE
    """)
    op.execute("""
        COMMENT ON TABLE couche_b.procurement_dict_families IS
        'DEPRECATED M7.3b — artefact M6.
         Référence : ADR-0016.
         Source de vérité : taxo_l1_domains/taxo_l2_families/taxo_l3_subfamilies'
    """)
    op.execute("""
        COMMENT ON COLUMN couche_b.procurement_dict_items.family_id IS
        'LEGACY M6 — READ-ONLY historique.
         Référence : ADR-0016 · RÈGLE-DICT-01.
         Utiliser domain_id / family_l2_id / subfamily_id (M7.2)'
    """)

    # 2 · Fonction de blocage
    op.execute("""
        CREATE OR REPLACE FUNCTION
            couche_b.fn_block_legacy_family_write()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'LEGACY family_id interdit après M7.3b (ADR-0016). '
                'Utiliser domain_id/family_l2_id/subfamily_id. '
                'item_id: %',
                NEW.item_id;
        END;
        $$
    """)

    # 3 · Trigger INSERT · OLD absent sur INSERT · PIÈGE-M7-04
    op.execute("""
        DROP TRIGGER IF EXISTS trg_block_legacy_family_insert
        ON couche_b.procurement_dict_items
    """)
    op.execute("""
        CREATE TRIGGER trg_block_legacy_family_insert
        BEFORE INSERT
        ON couche_b.procurement_dict_items
        FOR EACH ROW
        WHEN (NEW.family_id IS NOT NULL)
        EXECUTE FUNCTION couche_b.fn_block_legacy_family_write()
    """)

    # 4 · Trigger UPDATE · OLD disponible · sécurisé
    op.execute("""
        DROP TRIGGER IF EXISTS trg_block_legacy_family_update
        ON couche_b.procurement_dict_items
    """)
    op.execute("""
        CREATE TRIGGER trg_block_legacy_family_update
        BEFORE UPDATE OF family_id
        ON couche_b.procurement_dict_items
        FOR EACH ROW
        WHEN (OLD.family_id IS DISTINCT FROM NEW.family_id
              AND NEW.family_id IS NOT NULL)
        EXECUTE FUNCTION couche_b.fn_block_legacy_family_write()
    """)

    # 5 · Vue lecture seule historique
    op.execute("""
        CREATE OR REPLACE VIEW
            couche_b.legacy_procurement_families AS
        SELECT
            family_id,
            label_fr,
            criticite,
            deprecated,
            'DEPRECATED_M7.3b_ADR-0016' AS status_note
        FROM couche_b.procurement_dict_families
    """)

    # 6 · Vérification fail-loud
    op.execute("""
        DO $$
        DECLARE
            v_insert INTEGER;
            v_update INTEGER;
        BEGIN
            SELECT COUNT(*) INTO v_insert
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name = 'trg_block_legacy_family_insert';

            SELECT COUNT(*) INTO v_update
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name = 'trg_block_legacy_family_update';

            IF v_insert = 0 THEN
                RAISE EXCEPTION
                    'trg_block_legacy_family_insert absent — M7.3b KO';
            END IF;
            IF v_update = 0 THEN
                RAISE EXCEPTION
                    'trg_block_legacy_family_update absent — M7.3b KO';
            END IF;

            RAISE NOTICE
                'M7.3b OK — triggers legacy INSERT+UPDATE actifs (ADR-0016)';
        END;
        $$
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_block_legacy_family_update
        ON couche_b.procurement_dict_items
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_block_legacy_family_insert
        ON couche_b.procurement_dict_items
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
            couche_b.fn_block_legacy_family_write() CASCADE
    """)
    op.execute("""
        DROP VIEW IF EXISTS couche_b.legacy_procurement_families
    """)
    op.execute("""
        ALTER TABLE couche_b.procurement_dict_families
        DROP COLUMN IF EXISTS deprecated
    """)
```

---

## TEMPS 4 — APPLICATION ET CYCLE

```bash
alembic upgrade head
# Poster output · STOP si erreur

alembic heads
# Attendu : m7_3b_deprecate_legacy_families · 1 seul résultat

alembic downgrade -1
alembic upgrade head
alembic heads
# Cycle propre · 0 erreur · poster les 3 outputs
```

---

## TEMPS 5 — TESTS · RÈGLE-17

```python
# tests/dict/test_m7_3b_legacy_block.py
"""
Tests M7.3b · RÈGLE-17
Invariant : family_id bloqué en écriture · lectures OK.
"""
from __future__ import annotations
import pytest
import psycopg
from psycopg.rows import dict_row


@pytest.fixture
def conn(db_url: str):
    with psycopg.connect(db_url, row_factory=dict_row) as c:
        yield c


class TestLegacyFamilyBlock:

    def test_insert_avec_family_id_bloque(self, conn):
        """INSERT avec family_id non null → exception LEGACY."""
        with pytest.raises(psycopg.errors.RaiseException) as exc:
            conn.execute("""
                INSERT INTO couche_b.procurement_dict_items
                    (item_id, label_fr, canonical_slug,
                     active, family_id)
                VALUES
                    ('_test_insert_legacy_block',
                     'Test trigger insert',
                     '_test_insert_legacy_block',
                     TRUE, 'equipements')
            """)
        assert "LEGACY family_id interdit" in str(exc.value)

    def test_insert_sans_family_id_passe(self, conn):
        """INSERT sans family_id → OK."""
        conn.execute("""
            INSERT INTO couche_b.procurement_dict_items
                (item_id, label_fr, canonical_slug, active)
            VALUES
                ('_test_insert_no_family',
                 'Test sans family',
                 '_test_insert_no_family',
                 TRUE)
            ON CONFLICT (item_id) DO NOTHING
        """)
        r = conn.execute("""
            SELECT item_id FROM couche_b.procurement_dict_items
            WHERE item_id = '_test_insert_no_family'
        """).fetchone()
        assert r is not None

    def test_update_family_id_bloque(self, conn):
        """UPDATE family_id vers nouvelle valeur → exception LEGACY."""
        conn.execute("""
            INSERT INTO couche_b.procurement_dict_items
                (item_id, label_fr, canonical_slug, active)
            VALUES
                ('_test_update_legacy_block',
                 'Test update legacy',
                 '_test_update_legacy_block',
                 TRUE)
            ON CONFLICT (item_id) DO NOTHING
        """)
        with pytest.raises(psycopg.errors.RaiseException) as exc:
            conn.execute("""
                UPDATE couche_b.procurement_dict_items
                SET family_id = 'carburants'
                WHERE item_id = '_test_update_legacy_block'
            """)
        assert "LEGACY family_id interdit" in str(exc.value)

    def test_lecture_family_id_autorisee(self, conn):
        """SELECT family_id existant → OK · lectures non bloquées."""
        r = conn.execute("""
            SELECT family_id
            FROM couche_b.procurement_dict_items
            WHERE active = TRUE
            LIMIT 1
        """).fetchone()
        assert r is not None

    def test_vue_legacy_lisible(self, conn):
        """Vue legacy_procurement_families accessible · status_note correct."""
        rows = conn.execute("""
            SELECT family_id, status_note
            FROM couche_b.legacy_procurement_families
            LIMIT 1
        """).fetchall()
        assert isinstance(rows, list)
        if rows:
            assert rows[0]["status_note"] == "DEPRECATED_M7.3b_ADR-0016"

    def test_deux_triggers_actifs(self, conn):
        """Deux triggers INSERT + UPDATE actifs · invariant M7.3b."""
        r = conn.execute("""
            SELECT COUNT(*) AS n
            FROM information_schema.triggers
            WHERE event_object_schema = 'couche_b'
              AND event_object_table  = 'procurement_dict_items'
              AND trigger_name IN (
                'trg_block_legacy_family_insert',
                'trg_block_legacy_family_update'
              )
        """).fetchone()
        assert r["n"] == 2

    def test_alembic_head(self, conn):
        """HEAD = m7_3b_deprecate_legacy_families."""
        r = conn.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        assert r["version_num"] == "m7_3b_deprecate_legacy_families"
```

```bash
pytest tests/dict/test_m7_3b_legacy_block.py -v --tb=short
# Attendu : 7 passed · 0 failed
```

**Poster output complet.**

---

## TEMPS 6 — PROBE POST-MIGRATION

```sql
SELECT
    COUNT(*) FILTER (
        WHERE domain_id IS NULL
          AND human_validated = FALSE
    ) AS items_sans_taxonomie,
    (
        SELECT COUNT(*)
        FROM information_schema.triggers
        WHERE event_object_schema = 'couche_b'
          AND event_object_table  = 'procurement_dict_items'
          AND trigger_name IN (
            'trg_block_legacy_family_insert',
            'trg_block_legacy_family_update'
          )
    ) AS triggers_actifs
FROM couche_b.procurement_dict_items;
```

```text
CONDITION GO :
  triggers_actifs = 2            ← OBLIGATOIRE · STOP-L3 si ≠ 2
  items_sans_taxonomie           ← contexte · sera résolu par M7 réel
```

**Poster output. STOP si triggers_actifs ≠ 2.**

---

## TEMPS 7 — VALIDATION FINALE

```bash
pytest -q --tb=short 2>&1 | tail -10
# 0 failed · 0 errors

ruff check . && black --check .
# verts

grep -rn "m7_3_dict_nerve_center" tests/
# Si présent → mettre à jour vers m7_3b_deprecate_legacy_families
```

**Poster 3 outputs.**

---

## TEMPS 8 — MERGE ET TAG

```bash
# 7 gates ADR-MERGE-001
# 1. alembic heads = 1
# 2. alembic history down_revision correct
# 3. alembic upgrade head 0 erreur
# 4. cycle down/up stable
# 5. pytest -q 0 failed
# 6. ruff + black verts
# 7. fichiers hors périmètre = 0

git tag v4.2.0-m7-3b-legacy-deprecated
git push origin feat/m7-3b-deprecate-legacy --tags
# PR → GO CTO → merge main
```

---

## APRÈS MERGE — M7 RÉEL · SÉQUENCE IMMÉDIATE

```text
M7.3b mergé = infrastructure béton.

Reprendre le plan V4.1.0 exactement :

ÉTAPE 1 · scripts/classify_taxo.py
  Lit procurement_dict_items · domain_id IS NULL
  3 niveaux : seed_exact · trgm · llm_mistral
  Peuple taxo_proposals_v2 · status=pending/approved/flagged
  Zéro UPDATE sur procurement_dict_items (RÈGLE-M7-03)
  Branche : feat/m7-classify-taxo

ÉTAPE 2 · Validation humaine AO
  Review taxo_proposals_v2 status=pending
  Priorité familles CRITIQUE :
    CARB_LUB · ALIM_VIVRES · SANTE · VEHICULES_ENGINS
  human_validated = TRUE sur items validés
  RÈGLE-25 : AO valide · LLM propose · jamais l'inverse

ÉTAPE 3 · scripts/seed_apply_taxo.py
  Copie domain_id/family_l2_id/subfamily_id
  depuis taxo_proposals_v2 status=approved
  vers procurement_dict_items
  Idempotent · RÈGLE-N02
  Branche : feat/m7-apply-taxo

ÉTAPE 4 · Validation KPI
  résiduel DIVERS_NON_CLASSE ≤ 25%
  quality_score moyen > 60
  51 seeds = domain_id non null · human_validated = TRUE
  Tag : v4.2.0-m7-dict-vivant

ALORS : M8 débloqué · M9 débloqué
```

---

## CONDITION DONE COMPLÈTE

```text
[ ] ADR-0016 committé avant migration
[ ] probe L1→L7 posté · grep L8 = 0 écriture family_id
[ ] down_revision = valeur L1 copiée
[ ] deux triggers séparés INSERT + UPDATE
[ ] DO $$ vérification : 2 triggers actifs
[ ] cycle downgrade + upgrade → 0 erreur
[ ] 7 tests passent · 0 failed
[ ] probe TEMPS 6 : triggers_actifs = 2
[ ] pytest global → 0 failed
[ ] ruff + black → verts
[ ] alembic heads → 1 · m7_3b_deprecate_legacy_families
[ ] tag : v4.2.0-m7-3b-legacy-deprecated
[ ] PR mergée · main stable
[ ] feat/m7-classify-taxo ouverte · M7 réel démarré
```

---

*DMS V4.2.0 · Tech Lead · M7.3b + ADR-0016*
*Détour documenté · Infrastructure béton · Retour plan V4.1.0*
*family\_id = lecture seule · domain\_id/family\_l2\_id/subfamily\_id = vérité*
*Mopti · Mali · 2026*
