# 📘 PLAN D'EXÉCUTION SYSTÈME — DMS V3.3.2 FREEZE (VERSION FINALE CANONIQUE)

**Document d'ingénierie canonique — exécutable (repo-ready)**  
**Auteur**: Abdoulaye Ousmane  
**Rôle**: Founder & CTO — System Engineer · Tech Lead · Procurement Analyst  
**Statut**: ✅ OFFICIEL · OPPOSABLE · FREEZE  
**Date freeze**: 15 février 2026, 17:45 CET  
**Référence**: Constitution DMS V3.3.1 (FREEZE CANONIQUE) + Patch freeze V3.3.1 (SLA dual-class, INV-4/INV-9, Redis qualifié, entité documents/extractions/extraction_corrections, “zéro saisie manuelle répétitive”, Python 3.11+ précisé)

---

## 🔐 TRAÇABILITÉ OPPOSABLE (À RENSEIGNER / AUTO-CALCUL POST-FREEZE)

> **Règle opposable** : ce document n’a de valeur opérationnelle que si les empreintes (hash) et le commit de référence sont renseignés après “freeze”.

```yaml
Repository:
  url: https://github.com/[organization]/dms-v3
  branch: fix/a11y-wcag-a
  commit_sha: "[REMPLIR: git rev-parse HEAD]"

Audit source:
  audit_id: audit_20260215_124514
  report_json: docs/audits/LOCKING_AUDIT_20260215.json
  report_md: docs/LOCKING_AUDIT_REPORT.md

Constitution:
  version: V3.3.1
  path: docs/CONSTITUTION_DMS_V3.3.1.md
  hash_sha256: "[REMPLIR: sha256sum docs/CONSTITUTION_DMS_V3.3.1.md]"

Execution Plan:
  version: V3.3.1-FINAL
  path: docs/MILESTONES_EXECUTION_PLAN_V3.3.1_FREEZE.md
  hash_sha256: "[AUTO-CALCULÉ POST-FREEZE]"
  signed_by: "Abdoulaye Ousmane (CTO)"
  signature_date: "2026-02-15"
________________________________________
📊 ÉTAT DES LIEUX (AUDIT 2026-02-15)
Repository (audit snapshot)
Fichiers Python: 70
Base de données: PostgreSQL (provisionnée)
CI Status: ✅ VERTE
Stack: FastAPI, JWT, templates CBA/PV

Milestones DONE technique:
  ✅ M4A (Refactor DB)
  ✅ M-REFACTOR
  ✅ M3A (Critères typés)
  ✅ M3B (Scoring engine)
  ✅ M6 (Génération CBA/PV)
  ✅ M9 (Sécurité JWT/RBAC)   # présent mais à compléter par IAM/PolicyGate

Milestones PARTIELS:
  ⚠️ M2 (Ingestion): mécanisme présent, 0/80 offres ingérées
  ⚠️ M-TESTS: coverage non mesuré (objectif ≥40% baseline)
  ⚠️ M8 (Couche B): REST API absente (et audit mémoire non formalisé)

Milestones NON DÉMARRÉS:
  ❌ M11 (Monitoring): structlog, prometheus absents
  ❌ M-DICT (Dictionnaire procurement)
  ❌ M-MARKET-SIGNAL (3 sources de vérité)
  ❌ M-DOCS-CORE (documents/extractions/corrections gate)
  ❌ IAM/Comité/PolicyGate (accès par participation)

Données disponibles:
  - 2 DAO (40 offres chacun = 80 total)
  - 0/80 offres ingérées ⚠️ BLOCAGE CRITIQUE

Verdict audit: NO-GO
  Raisons:
    - ingestion non opérationnelle (0/80)
    - Railway non vérifié (non auditable)
    - coverage non mesuré (gate absent)
    - IAM/committee/policy absents (sécurité logique)
    - monitoring absent (prod readiness)
________________________________________
🎯 PRINCIPES D'EXÉCUTION (NON NÉGOCIABLES — OPPOSABLES)
1) Exécution séquentielle stricte
Aucun milestone ne démarre tant que les critères de sortie du précédent ne sont pas validés.
2) Un milestone = un sous-système stable
Pas de “80% fait”. Soit le module est exploitable en production, soit il n’existe pas.
Tout code non testé est considéré comme non écrit.
3) Zéro contournement du dictionnaire procurement
Toute donnée métier (item, unité, fournisseur) manipulée sans passer par le dictionnaire procurement est un bug de niveau 1.
4) Chaque invariant constitutionnel est testable
Les 9 invariants (INV-1 à INV-9) doivent avoir des tests CI automatisés.
Tout ce qui n'est pas testable en CI est considéré comme non implémenté.
5) Coverage gate strict (progressif, opposable)
Seuils progressifs (non négociables):
  Phase 0-1 (Baseline):    ≥40%
  Phase 2-3 (Alpha):       ≥60%
  Phase 4-5 (Beta):        ≥75%
  Phase 6-7 (Production):  ≥85%

Modules critiques (renforcés):
  src/scoring/:     ≥90%
  src/dictionary/:  ≥90%
  src/security/:    ≥95%
  src/extraction/:  ≥85%
CI bloque tout merge si coverage régresse.
6) Budget ≠ excuse
Terminologie:
  "Budget: X jours" = temps alloué milestone

Règle opposable:
  Le dépassement du budget n'autorise JAMAIS:
    ❌ Réduction des tests obligatoires
    ❌ Skip de gates CI
    ❌ Baisse du seuil coverage
    ❌ Contournement des invariants

En cas dépassement:
  1. STOP exécution
  2. Analyse root cause
  3. Décision CTO: ajuster budget OU revoir scope OU accepter retard
7) NO-GO automatique
Si un des critères suivants n’est pas rempli, le milestone est REJETÉ :
•	❌ 1+ test failing
•	❌ Coverage sous seuil
•	❌ CI rouge
•	❌ Invariant constitutionnel violé
•	❌ SLA non respecté (§7 Constitution)
•	❌ Migration échoue
•	❌ Rollback impossible
________________________________________
🧠 ARCHITECTURE OPPOSABLE DE LA TRAÇABILITÉ (ANTI-SHAREPOINT)
Règle canonique : la traçabilité est un système à deux étages.
L’étage A est un ledger append-only opposable. L’étage B est une mémoire vivante (coupe, classe, explique) mais ne réécrit jamais l’histoire.
Niveau A — Ledger opposable (Couche A / DB)
•	audit_log (append-only) : événements sensibles (création case, upload doc, extraction, correction, scoring, décision, export).
•	extraction_corrections (append-only) : corrections humaines before/after.
•	score_history (append-only) : historiques des scores.
•	elimination_log (append-only) : historiques des éliminations.
Interdiction opposable : audit “type SharePoint” (= dépôt de fichiers et notes sans structure).
Le dépôt de pièces est dans documents, la traçabilité est dans les tables append-only.
Niveau B — Mémoire vivante (Couche B)
•	Consomme le ledger A (sans le modifier).
•	Produit :
o	timeline par case,
o	recherche filtrée par droits,
o	explications structurées,
o	FAQ procédure (générale) et clarifications (sans fuite cross-case).
•	LLM : post-MVP stable, jamais source de vérité (voir section dédiée).
________________________________________
🔐 MODÈLE D’ACCÈS OPPOSABLE (IAM + COMITÉ + POLICY GATE)
Règle centrale : un membre de comité ne voit que les processus auxquels il a participé (membership).
Pour le reste, il interroge la Couche B en procédure générale (sans données case-confidentielles d’autres dossiers).
RBAC (rôles)
Rôles canoniques :
•	admin
•	procurement_manager
•	procurement_user
•	committee_member
•	auditor
ABAC (membership par case)
•	case_membership est la source de vérité des accès “par participation”.
Policies opposables (résumé)
Policy P-CASE-READ:
  allow if:
    - role in [admin]
    OR
    - role == auditor AND auditor_scope == global   # si autorisé globalement
    OR
    - case_membership exists(case_id, user_id)
  deny otherwise

Policy P-CASE-WRITE:
  allow if:
    - role in [admin, procurement_manager]
    OR
    - case_membership.role in [owner, editor]
  deny otherwise

Policy P-COMMITTEE:
  committee_member:
    - read allowed only via membership
    - write limited (option) à observations/notes sur le case assigné
  deny cross-case
________________________________________
✅ MILESTONES — ORDRE CANONIQUE, EXÉCUTION CHIRURGICALE ET DISCIPLINÉE
Règle d’ordre (FK) : cases doit exister avant documents (car documents.case_id -> cases.id).
Le plan ci-dessous respecte cette contrainte.
________________________________________
PHASE 0 — STABILISATION RUNTIME & CI GATES (BLOCAGE ABSOLU)
M0.1 — BOOT & HEALTH CHECK
Module: Infrastructure / Runtime
Priorité: 🔴 BLOQUANT ABSOLU
Budget: 0.5 jour
Objectif
Garantir que le système démarre, répond, et peut être audité en production.
Artefacts à produire
# src/api/health.py
@router.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "migrations": "up_to_date",
        "version": "v3.3.1"
    }
Tests obligatoires
def test_health_endpoint_returns_200():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_health_checks_db_connection():
    # Simuler DB down → doit retourner 503
    pass
Conditions de sortie
•	uvicorn main:app démarre sans exception
•	/api/health retourne 200 OK avec payload structuré
•	Railway accessible et répond à /api/health
•	Alembic migrations applicables
•	CI verte
________________________________________
M0.2 — CI COVERAGE GATE (Baseline)
Module: CI / Testing Infrastructure
Priorité: 🔴 BLOQUANT
Budget: 0.5 jour
Objectif
Installer coverage tracking et bloquer toute régression.
Artefacts à produire
# .github/workflows/ci.yml
- name: Run tests with coverage
  run: |
    pip install pytest-cov
    pytest --cov=src --cov-report=term-missing --cov-fail-under=40
Conditions de sortie
•	pytest-cov installé
•	Coverage mesuré en CI
•	Seuil 40% configuré et bloquant
•	Badge GitHub coverage (si utilisé)
________________________________________
PHASE 1 — IAM / COMITÉ / POLICY GATE (BLOCAGE MVP)
M1.0 — IAM-CORE (Users, Roles, Sessions)
Module: src/security/ + src/models/ + src/api/admin/
Priorité: 🔴 BLOQUANT ABSOLU
Budget: 1 jour
Objectif
Créer une base opposable de gestion utilisateurs + rôles, liée au JWT existant.
Tables requises
CREATE TABLE users (
    id VARCHAR(100) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE user_roles (
    user_id VARCHAR(100) REFERENCES users(id) ON DELETE CASCADE,
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by VARCHAR(100),
    PRIMARY KEY (user_id, role_id)
);

-- Seed rôles canoniques:
-- admin, procurement_manager, procurement_user, committee_member, auditor
Endpoints obligatoires
•	POST /api/admin/users (admin-only)
•	GET /api/admin/users (admin-only)
•	POST /api/admin/users/{user_id}/roles (admin-only)
•	GET /api/me (auth)
Tests obligatoires
def test_admin_can_create_user():
    pass

def test_non_admin_cannot_create_user():
    pass

def test_user_roles_attached():
    pass
Conditions de sortie
•	Tables migrées Alembic
•	Rôles seedés (5 rôles)
•	Endpoints admin fonctionnels
•	Tests RBAC passent
•	Aucune route sensible accessible sans auth
________________________________________
M1.1 — CASE ACCESS CONTROL (ABAC Membership / PolicyGate)
Module: src/security/policy_gate.py + src/models/access.py + intégration routes
Priorité: 🔴 BLOQUANT ABSOLU
Budget: 1 jour
Objectif
Implémenter la règle d’accès “par participation” et empêcher toute fuite cross-case.
Tables requises
CREATE TABLE case_membership (
    case_id VARCHAR(100) REFERENCES cases(id) ON DELETE CASCADE,
    user_id VARCHAR(100) REFERENCES users(id) ON DELETE CASCADE,
    membership_role VARCHAR(50) NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    added_by VARCHAR(100),
    PRIMARY KEY (case_id, user_id)
);

-- membership_role: owner | editor | committee | viewer | auditor
CREATE INDEX idx_case_membership_user ON case_membership(user_id);
CREATE INDEX idx_case_membership_case ON case_membership(case_id);
Politique opposable (implémentation)
•	Toute route case-scoped doit passer par PolicyGate.assert_case_read(case_id, user)
•	Toute route d’écriture case-scoped doit passer par PolicyGate.assert_case_write(case_id, user)
Tests obligatoires
def test_committee_member_sees_only_assigned_cases():
    pass

def test_committee_member_cannot_read_other_case():
    pass

def test_procurement_user_without_membership_cannot_access_case():
    pass

def test_admin_can_access_all_cases():
    pass
Conditions de sortie
•	case_membership migrée
•	PolicyGate appliqué à toutes les routes case
•	Zéro route case sans check
•	Tests ABAC passent
________________________________________
M1.2 — COMMITTEE MODEL (Structure, PV, Gouvernance)
Module: src/models/committee.py + endpoints admin
Priorité: 🟡 HAUTE
Budget: 0.5 jour
Objectif
Formaliser un comité comme entité (utile PV + gouvernance).
Note opposable : l’autorisation d’accès reste case_membership.
Tables
CREATE TABLE committees (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE TABLE committee_members (
    committee_id VARCHAR(100) REFERENCES committees(id) ON DELETE CASCADE,
    user_id VARCHAR(100) REFERENCES users(id) ON DELETE CASCADE,
    role_in_committee VARCHAR(50),
    added_at TIMESTAMP DEFAULT NOW(),
    added_by VARCHAR(100),
    PRIMARY KEY (committee_id, user_id)
);

CREATE TABLE case_committees (
    case_id VARCHAR(100) REFERENCES cases(id) ON DELETE CASCADE,
    committee_id VARCHAR(100) REFERENCES committees(id) ON DELETE CASCADE,
    PRIMARY KEY (case_id, committee_id)
);
Conditions de sortie
•	Entités comité créées
•	Un case peut être lié à 1+ comités
•	Le comité n’ouvre aucun accès sans membership
________________________________________
PHASE 2 — FONDATIONS DONNÉES COUCHE A (SCHÉMA CANONIQUE)
M2.1 — ENTITÉS COUCHE A CORE (cases, suppliers, offers, criteria)
Module: src/models/
Priorité: 🔴 BLOQUANT
Budget: 0.5 jour
Objectif
Vérifier et compléter le schéma de données Couche A (§6.2 Constitution).
Tables requises
CREATE TABLE cases (
    id VARCHAR(100) PRIMARY KEY,
    reference VARCHAR(100) UNIQUE NOT NULL,
    process_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name_canonical VARCHAR(255) UNIQUE NOT NULL,
    aliases TEXT[],
    tin VARCHAR(50),
    history JSONB DEFAULT '{}'
);

CREATE TABLE offers (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(100) REFERENCES cases(id),
    supplier_id INT REFERENCES suppliers(id),
    items JSONB NOT NULL,
    total_price NUMERIC(12,2),
    currency VARCHAR(10),
    submitted_at TIMESTAMP,
    UNIQUE(case_id, supplier_id)
);

CREATE TABLE criteria (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(100) REFERENCES cases(id),
    name TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL,
    weight NUMERIC(5,2),
    formula TEXT,
    expected_value TEXT
);
Tests obligatoires
def test_core_tables_exist():
    tables = ["cases", "suppliers", "offers", "criteria"]
    for table in tables:
        assert table_exists(table)

def test_foreign_keys_enforced():
    with pytest.raises(IntegrityError):
        db.execute("INSERT INTO offers (case_id, supplier_id) VALUES ('fake', 1)")
Conditions de sortie
•	4 tables validées
•	Foreign keys actives
•	Seed: 1 cas test complet
•	Migration Alembic propre
________________________________________
M2.2 — DOCS-CORE (Documents / Extractions / Corrections) — Point d’entrée canonique
Module: src/documents/
Priorité: 🔴 BLOQUANT ABSOLU (Constitution §6.1 + patch freeze)
Budget: 0.5 jour
Objectif
Établir le point d’entrée unique de toutes les données système (upload -> intégrité -> statut -> extraction -> corrections tracées).
Tables requises (Constitution §6.1)
CREATE TABLE documents (
    id VARCHAR(100) PRIMARY KEY,
    case_id VARCHAR(100) REFERENCES cases(id),
    kind VARCHAR(50) NOT NULL,
    filename TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    page_count INT,
    extraction_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE TABLE extractions (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(100) REFERENCES documents(id) ON DELETE CASCADE,
    page_number INT,
    raw_text TEXT,
    structured_data JSONB,
    extraction_method VARCHAR(50),
    confidence_score NUMERIC(5,2),
    extracted_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE extraction_corrections (
    id SERIAL PRIMARY KEY,
    extraction_id INT REFERENCES extractions(id),
    field_path TEXT NOT NULL,
    value_before TEXT NOT NULL,
    value_after TEXT NOT NULL,
    reason TEXT,
    corrected_by VARCHAR(100) NOT NULL,
    corrected_at TIMESTAMP DEFAULT NOW()
);

-- Append-only (bloquer DELETE/UPDATE) - via triggers ou privileges DB selon stratégie
Exigences non négociables
•	SHA256 calculé à l’upload
•	MIME validé par magic bytes (pas extension)
•	extraction_status piloté (pending/processing/done/failed)
•	Corrections humaines: append-only with before/after (INV-9 patch)
Tests obligatoires
def test_documents_table_exists():
    assert table_exists("documents")
    assert table_exists("extractions")
    assert table_exists("extraction_corrections")

def test_extraction_corrections_append_only():
    with pytest.raises(OperationalError):
        db.execute("DELETE FROM extraction_corrections WHERE id = 1")
Conditions de sortie
•	3 tables validées
•	Upload calcule sha256
•	Validation mime par magic bytes
•	Append-only corrections testé
________________________________________
PHASE 3 — DONNÉES OPÉRATIONNELLES (BLOCAGE NO-GO)
M3.1 — INGESTION DAO CORPUS (80 offres réelles)
Module: src/ingestion/ + scripts
Priorité: 🔴 BLOQUANT NO-GO
Budget: 1 jour
Objectif
Ingérer les 80 offres (2 DAO × 40) pour avoir des données réelles exploitables.
Artefacts à produire
# scripts/ingest_dao.py
def ingest_dao_corpus():
    dao_01 = load_dao("data/dao_01.xlsx")
    dao_02 = load_dao("data/dao_02.xlsx")

    with db.session() as session:
        for dao in [dao_01, dao_02]:
            case = create_case(dao)
            criteria = extract_criteria(dao)
            offers = extract_offers(dao)
            session.add_all([case] + criteria + offers)
        session.commit()
Tests obligatoires
def test_dao_corpus_ingested():
    cases = db.query(Case).all()
    assert len(cases) == 2

    offers = db.query(Offer).all()
    assert len(offers) == 80
Conditions de sortie
•	2 cases créés
•	80 offers ingérées
•	~10 suppliers créés
•	~20 criteria typés
•	Script reproductible et documenté
________________________________________
PHASE 4 — DICTIONNAIRE PROCUREMENT (COLONNE VERTÉBRALE OBLIGATOIRE)
M4.1 — DICT FOUNDATION & SCHEMA
Module: src/dictionary/
Priorité: 🔴 CRITIQUE (Constitution §2.3)
Budget: 2 jours
Objectif
Créer l’infrastructure canonique de normalisation items/unités/fournisseurs.
Tables à créer
CREATE TABLE procurement_dictionary_items (
    id SERIAL PRIMARY KEY,
    item_name_canonical VARCHAR(255) UNIQUE NOT NULL,
    aliases TEXT[] NOT NULL DEFAULT '{}',
    category_code VARCHAR(50),
    mercuriale_ref JSONB,
    unit_canonical VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_items_name_trgm ON procurement_dictionary_items USING gin(item_name_canonical gin_trgm_ops);
CREATE INDEX idx_items_aliases_trgm ON procurement_dictionary_items USING gin(aliases gin_trgm_ops);

CREATE TABLE procurement_dictionary_units (
    id SERIAL PRIMARY KEY,
    unit_canonical VARCHAR(50) UNIQUE NOT NULL,
    unit_aliases TEXT[] NOT NULL DEFAULT '{}',
    conversion_to_base JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE procurement_dictionary_vendors (
    id SERIAL PRIMARY KEY,
    vendor_name_canonical VARCHAR(255) UNIQUE NOT NULL,
    aliases TEXT[] NOT NULL DEFAULT '{}',
    tin VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dictionary_resolutions_log (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    input_value TEXT NOT NULL,
    resolved_to VARCHAR(255),
    confidence_score NUMERIC(5,2),
    method VARCHAR(50),
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMP DEFAULT NOW()
);
Seed data obligatoire
SEED_ITEMS = [
    {"canonical": "Rame papier A4 80g", "aliases": ["papier A4", "rame A4", "papier photocopie"], "category": "fournitures_bureau", "unit": "rame"},
    # ... 50+ items minimum
]
SEED_UNITS = [
    # ... 10+ unités minimum (avec conversions si applicable)
]
SEED_VENDORS = [
    # ... 20+ vendors minimum
]
Tests obligatoires
def test_dictionary_tables_exist():
    assert table_exists("procurement_dictionary_items")
    assert table_exists("procurement_dictionary_units")
    assert table_exists("procurement_dictionary_vendors")
    assert table_exists("dictionary_resolutions_log")

def test_trigram_indexes_created():
    indexes = get_indexes("procurement_dictionary_items")
    assert any("trgm" in idx for idx in indexes)

def test_seed_data_loaded():
    assert db.query(ProcurementItem).count() >= 50
    assert db.query(ProcurementUnit).count() >= 10
    assert db.query(ProcurementVendor).count() >= 20
Conditions de sortie
•	4 tables créées
•	Index trigram opérationnels
•	Seed ≥50 items, ≥10 unités, ≥20 vendors
•	Documentation README dictionnaire (structure, usage, seed)
________________________________________
M4.2 — DICT FUZZY MATCHING (items/units/vendors) + Logging
Module: src/dictionary/matching.py
Priorité: 🔴 CRITIQUE
Budget: 2 jours
Objectif
Implémenter fuzzy matching token-based + seuil configurable, avec log append-only des résolutions.
Algorithme (canon)
from rapidfuzz import fuzz, process

class DictionaryMatcher:
    CONFIDENCE_THRESHOLD = 80

    def resolve_item(self, input_item: str) -> dict:
        # 1. Exact match (canonical + aliases)
        exact = self._exact_match_item(input_item)
        if exact:
            self._log("item", input_item, exact, 100.0, "exact")
            return {"canonical": exact, "confidence": 100.0, "method": "exact"}

        # 2. Fuzzy
        candidates = self._candidate_items()
        best = process.extractOne(input_item, candidates, scorer=fuzz.token_sort_ratio)

        if best and best[1] >= self.CONFIDENCE_THRESHOLD:
            canonical = self._canonical_from_candidate(best[0])
            self._log("item", input_item, canonical, float(best[1]), "fuzzy")
            return {"canonical": canonical, "confidence": float(best[1]), "method": "fuzzy"}

        # 3. Manual required
        score = float(best[1]) if best else 0.0
        self._log("item", input_item, None, score, "manual_required")
        return {"canonical": None, "confidence": score, "method": "manual_required"}
Tests obligatoires
def test_exact_match_item():
    r = matcher.resolve_item("papier A4")
    assert r["canonical"] == "Rame papier A4 80g"
    assert r["confidence"] == 100.0
    assert r["method"] == "exact"

def test_fuzzy_match_above_threshold():
    r = matcher.resolve_item("papier A 4")
    assert r["canonical"] == "Rame papier A4 80g"
    assert r["confidence"] >= 80.0
    assert r["method"] == "fuzzy"

def test_fuzzy_match_performance_under_100ms():
    import time
    t0 = time.time()
    matcher.resolve_item("papier photocopie")
    assert (time.time() - t0) < 0.1

def test_resolution_logged():
    matcher.resolve_item("papier A4")
    row = db.query(DictionaryResolutionLog).filter_by(input_value="papier A4").first()
    assert row is not None
Conditions de sortie
•	DictionaryMatcher (items/units/vendors)
•	Seuil 80% configurable
•	Résolutions loggées append-only
•	Performance <100ms (SLA §7.3)
•	Endpoint POST /api/dictionary/resolve (si exposé) fonctionnel
________________________________________
M4.3 — NORMALISATION OFFERS (Gate avant scoring)
Module: src/normalization/
Priorité: 🔴 BLOQUANT SCORING
Budget: 1 jour
Objectif
Garantir qu’aucune offre brute ne passe au scoring sans normalisation dictionnaire.
Pipeline normalisation (canon)
class OfferNormalizer:
    def __init__(self, matcher: DictionaryMatcher):
        self.matcher = matcher

    def normalize_offer(self, offer: Offer) -> dict:
        normalized_items = []
        needs_validation = False

        for item in offer.items:
            item_res = self.matcher.resolve_item(item["name"])
            unit_res = self.matcher.resolve_unit(item["unit"])
            if item_res["method"] == "manual_required" or unit_res["method"] == "manual_required":
                needs_validation = True

            normalized_items.append({
                **item,
                "canonical_item": item_res["canonical"],
                "confidence_item": item_res["confidence"],
                "canonical_unit": unit_res["canonical"],
                "confidence_unit": unit_res["confidence"],
                "needs_validation": (item_res["method"] == "manual_required" or unit_res["method"] == "manual_required")
            })

        vendor_res = self.matcher.resolve_vendor(offer.supplier_name)

        return {
            "offer_id": offer.id,
            "supplier_canonical": vendor_res["canonical"],
            "items": normalized_items,
            "needs_validation": needs_validation
        }
Tests obligatoires
def test_no_raw_offer_in_scoring():
    raw_offer = Offer(items=[{"name": "papier", "unit": "rame"}])
    with pytest.raises(ValueError, match="Offer must be normalized"):
        scoring_engine.score(raw_offer)

def test_normalized_offer_has_canonical_fields():
    offer = Offer(items=[{"name": "papier A4", "unit": "rame"}])
    normalized = normalizer.normalize_offer(offer)
    assert normalized["items"][0]["canonical_item"] == "Rame papier A4 80g"
Conditions de sortie
•	OfferNormalizer implémenté
•	Normalisation intégrée à ingestion
•	Test “no raw offer in scoring” passing (bloquant)
•	80 offres corpus normalisées (résolues ou marquées validation)
________________________________________
PHASE 5 — MARKET SIGNAL (COUCHE B) — 3 SOURCES + READ-ONLY
M5.1 — MARKET DATA TABLES (3 sources de vérité)
Module: src/market/
Priorité: 🔴 BLOQUANT PRODUCTION (Constitution §3.2)
Budget: 1 jour
Tables à créer
CREATE TABLE mercurials (
    id SERIAL PRIMARY KEY,
    item_code VARCHAR(50) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    unit VARCHAR(50),
    zone VARCHAR(100),
    year INT NOT NULL,
    price_min NUMERIC(12,2),
    price_avg NUMERIC(12,2),
    price_max NUMERIC(12,2),
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(item_code, zone, year)
);

CREATE TABLE decision_history (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(100) REFERENCES cases(id),
    item_canonical VARCHAR(255),
    supplier_canonical VARCHAR(255),
    price_paid NUMERIC(12,2) NOT NULL,
    quantity NUMERIC(12,2),
    unit VARCHAR(50),
    decision_date DATE NOT NULL,
    zone VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE market_surveys (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(100) REFERENCES cases(id),
    item_canonical VARCHAR(255) NOT NULL,
    supplier_name VARCHAR(255) NOT NULL,
    price_quoted NUMERIC(12,2) NOT NULL,
    date_surveyed DATE NOT NULL,
    location VARCHAR(255),
    surveyor VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
Tests obligatoires
def test_market_data_tables_exist():
    assert table_exists("mercurials")
    assert table_exists("decision_history")
    assert table_exists("market_surveys")

def test_mercurials_seeded():
    count = db.query(Mercurial).filter_by(year=2026).count()
    assert count >= 100
Conditions de sortie
•	3 tables créées
•	Seed ≥100 items mercuriale 2026
•	Seed ≥50 entrées decision_history
•	Seed ≥30 market_surveys
________________________________________
M5.2 — MARKET SIGNAL ENGINE (priorité + fraîcheur + SLA <200ms)
Module: src/market/signal_engine.py
Priorité: 🔴 BLOQUANT PRODUCTION (Constitution §3.3-3.4)
Budget: 2 jours
Implémentation (canon)
from enum import Enum

class SignalQuality(str, Enum):
    FULL = "full"
    DEGRADED_2 = "degraded_2"
    DEGRADED_1 = "degraded_1"
    NO_DATA = "no_data"

class MarketSignalProvider:
    def get_signal(self, item_canonical: str, zone: str = "Bamako") -> dict:
        mercurial = self._get_mercurial(item_canonical, zone, max_age_years=2)
        history = self._get_decision_history(item_canonical, max_age_months=24)
        survey = self._get_market_survey(item_canonical, max_age_days=90)

        sources_available = sum([mercurial is not None, history is not None, survey is not None])

        if sources_available == 0:
            return {"quality": SignalQuality.NO_DATA, "sources_count": 0}

        if sources_available == 1:
            quality = SignalQuality.DEGRADED_1
        elif sources_available == 2:
            quality = SignalQuality.DEGRADED_2
        else:
            quality = SignalQuality.FULL

        # Priorité: survey > history > mercurial
        if survey:
            price_reference = survey["price_avg"]
            priority = "market_survey"
        elif history:
            price_reference = history["price_avg"]
            priority = "decision_history"
        else:
            price_reference = mercurial["price_avg"]
            priority = "mercurial"

        return {
            "item": item_canonical,
            "zone": zone,
            "quality": quality,
            "sources_count": sources_available,
            "priority_source": priority,
            "price_reference": price_reference,
            "mercurial": mercurial,
            "history": history,
            "survey": survey,
        }
Tests obligatoires
def test_market_signal_3_sources_full():
    s = provider.get_signal("Rame papier A4 80g")
    assert s["quality"] == SignalQuality.FULL

def test_market_signal_priority_survey_first():
    s = provider.get_signal("Rame papier A4 80g")
    assert s["priority_source"] == "market_survey"

def test_market_signal_query_under_200ms():
    import time
    t0 = time.time()
    provider.get_signal("Rame papier A4 80g")
    assert (time.time() - t0) < 0.2
Conditions de sortie
•	MarketSignalProvider implémenté
•	Priorité + fraîcheur testées
•	SLA <200ms passing
•	Endpoint API fonctionnel (si exposé)
________________________________________
M5.3 — MARKET SIGNAL UI PANEL (read-only, anti-prescription)
Module: frontend/
Priorité: 🟡 MOYENNE
Budget: 1 jour
Test invariant obligatoire
def test_market_signal_readonly():
    """INV-3: Market Signal ne modifie JAMAIS les scores"""
    with mock.patch("src.market.signal_engine.MarketSignalProvider.get_signal", return_value=None):
        scores_without = scoring_engine.calculate_scores("DAO-01")
    scores_with = scoring_engine.calculate_scores("DAO-01")
    assert scores_without == scores_with
Conditions de sortie
•	Panneau Market Signal visible en UI
•	3 sources affichées + qualité
•	Test read-only passing
________________________________________
PHASE 6 — AUDIT (LEDGER A + MÉMOIRE VIVANTE B)
M6.1 — AUDIT-LEDGER (Couche A append-only)
Module: src/audit/
Priorité: 🔴 BLOQUANT PRODUCTION
Budget: 1 jour
Objectif
Rendre la traçabilité opposable via ledger append-only.
Livrables
•	Table audit_log (si absente/incomplète)
•	Middleware AuditRecorder branché sur endpoints sensibles
•	Tests append-only (DELETE/UPDATE interdits)
Conditions de sortie
•	audit_log complet + events normalisés
•	recorder actif
•	append-only prouvé par tests
________________________________________
M6.2 — AUDIT-MEMORY (Couche B vivante, filtrée par PolicyGate)
Module: src/couche_b/audit_memory/
Priorité: 🟡 HAUTE
Budget: 1 jour
Objectif
Construire la “mémoire vivante” d’audit, sans fuite cross-case.
Endpoints (exemples)
•	GET /api/cases/{id}/timeline
•	GET /api/audit/search (filtré par PolicyGate)
Conditions de sortie
•	timeline case-scoped
•	search filtré
•	aucun accès cross-case possible via Couche B
________________________________________
PHASE 7 — MONITORING & OBSERVABILITÉ (PRODUCTION-READY)
M7.1 — LOGS STRUCTURÉS JSON
Module: src/logging/
Priorité: 🔴 BLOQUANT PRODUCTION
Budget: 1 jour
Implémentation
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
logger.info("offer_scored", case_id="DAO-01", supplier_id=5, score=85.5)
Tests obligatoires
def test_logs_are_json():
    with captured_logs() as logs:
        logger.info("test_event", foo="bar")
    log = json.loads(logs[0])
    assert "timestamp" in log
    assert log["event"] == "test_event"
Conditions de sortie
•	structlog installé
•	print() supprimés dans modules critiques
•	JSON validé
•	masquage données sensibles
________________________________________
M7.2 — MÉTRIQUES PROMETHEUS
Module: src/monitoring/metrics.py
Priorité: 🔴 BLOQUANT PRODUCTION
Budget: 1 jour
Métriques obligatoires
from prometheus_client import Counter, Histogram, Gauge

uploads_total = Counter("dms_uploads_total", "Documents uploadés")
cba_generated_total = Counter("dms_cba_generated_total", "CBA générés")

extraction_duration_seconds = Histogram(
    "dms_extraction_duration_seconds",
    "Durée extraction",
    buckets=[1, 5, 10, 15, 30, 60]
)

active_cases = Gauge("dms_active_cases", "Cas actifs")
Conditions de sortie
•	prometheus-client installé
•	endpoint /metrics exposé
•	métriques collectées sur actions réelles
________________________________________
PHASE 8 — TESTS INVARIANTS & SLA (FREEZE LOCK)
M8.1 — CI INVARIANTS SUITE (9 invariants)
Module: tests/invariants/
Priorité: 🔴 BLOQUANT FREEZE
Budget: 2 jours
Tests obligatoires (minimum)
# INV-1
def test_pipeline_under_60s():
    start = time.time()
    case_id = ingest_dao("dao_sample.xlsx")
    scoring_engine.calculate_scores(case_id)
    cba_generator.generate(case_id)
    assert time.time() - start < 60

# INV-2
def test_couche_a_standalone():
    with mock.patch("src.market.signal_engine.MarketSignalProvider", return_value=None):
        cba = cba_generator.generate(case_id)
        assert cba is not None

# INV-3
def test_scores_independent_of_couche_b():
    with mock.patch("MarketSignalProvider.get_signal", return_value=None):
        scores_without = scoring_engine.calculate_scores(case_id)
    scores_with = scoring_engine.calculate_scores(case_id)
    assert scores_without == scores_with

# INV-4 (online-first, pas d’offline durable)
def test_no_offline_components():
    pass

# INV-6 (append-only tables)
def test_audit_log_append_only():
    with pytest.raises(OperationalError):
        db.execute("DELETE FROM audit_log WHERE id = 1")

# INV-7 (ERP-agnostic)
def test_no_erp_dependency():
    pass

# INV-8 (docs)
def test_readme_exists():
    assert os.path.exists("README.md")

# INV-9 (fidélité + corrections tracées)
def test_score_equals_formula_output():
    score = scoring_engine.calculate_commercial_score(offer)
    expected = (800 / 1000) * 100
    assert abs(score - expected) < 0.01
Conditions de sortie
•	9 tests invariants implémentés
•	CI bloque merge si 1 invariant fail
•	docs/INVARIANTS.md rédigé (mapping tests ↔ Constitution)
________________________________________
M8.2 — PERF SLA & LOAD TESTS (Classe A/B + commun)
Module: tests/performance/
Priorité: 🔴 BLOQUANT PRODUCTION
Budget: 1 jour
Tests SLA (exemples)
def test_upload_extraction_under_15s():
    start = time.time()
    doc = upload_document("dao_native.pdf")
    extract_document(doc.id)
    assert time.time() - start < 15

def test_market_signal_query_under_200ms():
    start = time.time()
    provider.get_signal("Rame papier A4 80g")
    assert time.time() - start < 0.2
Conditions de sortie
•	SLA validés en CI
•	rapport performance doc
________________________________________
PHASE 9 — PRODUCTION READINESS (DOCS, SECURITY, DEPLOY)
M9.1 — DOCUMENTATION FINALE
Module: docs/
Priorité: 🟡 HAUTE
Budget: 1 jour
Artefacts
docs/
├── README.md
├── ARCHITECTURE.md
├── DATABASE_SCHEMA.md
├── API_REFERENCE.md
├── CONSTITUTION_DMS_V3.3.1.md
├── MILESTONES_EXECUTION_PLAN_V3.3.1_FREEZE.md
├── INVARIANTS.md
├── PERFORMANCE_SLA.md
├── DEPLOYMENT.md
├── USER_GUIDE.md
└── DEVELOPER_GUIDE.md
Conditions de sortie
•	10 docs rédigés
•	diagrammes + badges CI/coverage/invariants
________________________________________
M9.2 — SECURITY HARDENING
Module: src/security/
Priorité: 🔴 CRITIQUE
Budget: 1 jour
Checklist sécurité
Authentication:
  - [ ] JWT tokens avec expiration
  - [ ] Password hashing bcrypt (cost ≥12)

Authorization:
  - [ ] RBAC + ABAC (PolicyGate) testés

Input Validation:
  - [ ] Upload: magic bytes
  - [ ] Upload: taille max
  - [ ] SQL: requêtes paramétrées

Rate Limiting:
  - [ ] limites par user et IP

Secrets:
  - [ ] variables env uniquement

Audit:
  - [ ] actions sensibles loggées
Conditions de sortie
•	checklist validée
•	tests sécurité passent
•	docs/SECURITY.md
________________________________________
M9.3 — RAILWAY DEPLOYMENT VALIDATION
Module: Infrastructure
Priorité: 🔴 BLOQUANT NO-GO
Budget: 0.5 jour
Checklist Railway
Déploiement:
  - [ ] URL accessible
  - [ ] /api/health = 200
  - [ ] PostgreSQL connecté
  - [ ] migrations appliquées

Monitoring:
  - [ ] logs OK
  - [ ] /metrics OK
Conditions de sortie
•	Railway auditable
•	80 offres ingérées en prod
•	1 CBA généré en prod
________________________________________
PHASE 10 — GO / NO-GO + PILOT
M10.1 — PRE-PRODUCTION CHECKLIST
Module: Validation
Priorité: 🔴 GATE FINAL
Budget: 0.5 jour
Critères NO-GO (absolus)
•	Coverage < seuil phase
•	1+ invariant failing
•	1+ SLA non respecté
•	Railway inaccessible
•	0 offre ingérée
•	PolicyGate non appliqué partout
________________________________________
M10.2 — EARLY ADOPTERS PILOT
Module: Production
Priorité: 🟡 VALIDATION TERRAIN
Budget: 5 jours
Plan pilot
Utilisateurs:
  - 3 procurement officers SCI Mali
  - 1 finance
  - 1 comité passation

Règle comité:
  - comité_member voit uniquement les cases assignés (membership)

Métriques:
  - Temps Upload → CBA: <5 min (vs 2h Excel)
  - NPS: ≥40
  - % "je ne reviens pas à Excel": ≥80%
  - Bugs critiques: 0
________________________________________
🧬 ANNEXE A — DEFINITION OF DONE (UNIVERSELLE)
Un milestone est validé SI ET SEULEMENT SI:
Code
•	Ruff: 0 erreurs
•	mypy: 0 erreurs (si activé)
•	Aucun print() debug dans modules critiques
•	Aucun TODO/FIXME critique
•	Format appliqué (Black/Ruff)
Tests
•	unit tests écrits
•	0 failing
•	coverage ≥ seuil
•	E2E si applicable
•	perf/SLA si applicable
CI gates
•	CI verte
•	coverage gate respecté
•	aucun skip/xfail non justifié
Données
•	migrations Alembic testées
•	seed data (si requis)
•	contraintes DB actives
•	indexes créés
Sécurité
•	aucun secret en dur
•	validations inputs
•	PolicyGate appliqué aux routes case
•	audit ledger écrit sur actions sensibles
Constitution
•	aucun invariant violé
•	SLA respectés
•	dictionnaire utilisé
NO-GO AUTOMATIQUE SI:
•	❌ 1+ test failing
•	❌ coverage sous seuil
•	❌ CI rouge
•	❌ invariant violé
•	❌ SLA non respecté
•	❌ migration échoue
•	❌ PolicyGate absent sur une route case
________________________________________
🤖 ANNEXE B — LLM DANS LE PRODUIT (RÈGLE FREEZE)
Le LLM est prévu pour l’outil uniquement quand le MVP est suffisamment stable avec métriques claires.
Avant cela, Couche B fonctionne en déterministe (DB + règles + index).
Règles opposables
•	Le LLM n’est jamais une source de vérité.
•	Le LLM n’écrit jamais dans les tables ledger append-only.
•	Le LLM agit en assistant : FAQ procédure, clarification, synthèse, recherche sur index, aide lecture timeline.
•	L’activation LLM est gated par : coverage ≥75%, invariants 9/9, SLA validés, audit ledger solide.
________________________________________
🔒 STATUT FINAL — FREEZE OFFICIEL
Version: V3.3.1-FINAL
Statut: ✅ FREEZE OFFICIEL
Date: 15 février 2026, 17:45 CET
Signature: Abdoulaye Ousmane (CTO)

Ce document est désormais la référence canonique opposable.
Toute modification nécessite versioning (V3.3.2, V3.3.3...),
avec justification technique + analyse d’impact + validation CTO.
Prochaine action immédiate (ordre strict):
1.	M0.1 (Boot & Health Check)
2.	M0.2 (Coverage Gate)
3.	M1.0 (IAM-CORE)
4.	M1.1 (PolicyGate / case_membership)
5.	M2.1 (Cases/Suppliers/Offers/Criteria)
6.	M2.2 (Docs/Extractions/Corrections)
7.	M3.1 (Ingestion 80 offres)
FIN DU DOCUMENT FREEZE
