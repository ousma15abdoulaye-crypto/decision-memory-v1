# AUDIT M4→M7 — INVARIANTS ATOMIQUES

**Date :** 2026-03-08  
**Format :** Objet / Invariant / Preuve brute / Écart freeze / Sévérité / Risque / Verdict / Action future  
**Référence :** DMS V4.1.0 FREEZE DÉFINITIF

---

## A. Existence métier de l'item

**Objet :**  
`couche_b.procurement_dict_items`

**Invariant :**  
L'item existe indépendamment de sa taxonomie. La suppression ou l'invalidation d'une entrée taxonomique ne doit pas détruire l'item.

**Preuve brute :**  
Migration m7_2_taxonomy_reset.py :
```python
_add_col("couche_b", "procurement_dict_items", "domain_id",
    "TEXT REFERENCES couche_b.taxo_l1_domains(domain_id)")
_add_col("couche_b", "procurement_dict_items", "family_l2_id",
    "TEXT REFERENCES couche_b.taxo_l2_families(family_l2_id)")
_add_col("couche_b", "procurement_dict_items", "subfamily_id",
    "TEXT REFERENCES couche_b.taxo_l3_subfamilies(subfamily_id)")
```
Aucun `ON DELETE` spécifié → PostgreSQL applique `NO ACTION` par défaut.  
`NO ACTION` = le DELETE sur taxo échoue si des items le référencent (contrainte vérifiée en fin de transaction).  
Probe probe_post.txt : 1489 items actifs, 0 avec domain_id → tous items existent sans taxonomie assignée.

**Écart au freeze :**  
M6 construit un registre canonique depuis libellés réels M5. Les items doivent exister avant et indépendamment de toute taxonomie. La structure FK (domain_id nullable) préserve l'existence, mais introduit une dépendance structurelle : les items sans taxo ont des colonnes NULL qui affectent le quality_score via trigger (fn_compute_quality_score : domain_id non null → +30 pts). L'existence physique est préservée ; la qualité calculée est dépendante de la taxonomie.

**Sévérité :** S2 — dette réelle contenue

**Risque :**  
Suppression cascade indirecte impossible (NO ACTION). Mais logique métier (quality_score, classification_confidence) dépend de la taxonomie. Items sans taxo = citoyens de seconde zone dans le scoring.

**Verdict :**  
HYBRIDE — existence physique préservée, dépendance ontologique structurelle introduite

**Action future requise :**  
ADR séparation identité/registre/taxonomie. Le score de qualité ne doit pas dépendre de colonnes taxonomiques dans le trigger.

---

## B. Identité permanente de l'item

**Objet :**  
`item_id`, `item_uid`, `item_code` sur `couche_b.procurement_dict_items`

**Invariant :**  
L'identité item est stable, non dépendante d'un ordre SQL implicite, d'un ordre batch, du LLM, ni d'une classification mutable.

**Preuve brute :**  
`build_dictionary.py` (source normalizer) :
```python
from src.couche_b.dictionary.normalizer import (
    normalize_label, build_canonical_slug, generate_deterministic_id,
)
# item_id = generate_deterministic_id(slug) = SHA256(slug)[:16]
```
item_id = déterministe depuis le slug normalisé. Non dépendant de l'ordre SQL ni du LLM.

Migration m7_4a_item_identity_doctrine.py :
```python
# item_uid = TEXT UNIQUE (UUIDv7 — généré localement)
# item_code = TEXT UNIQUE (ITM.BD.BF.BS.SERIAL.CD — check digit Luhn)
# Backfill : human_validated = TRUE ET domain_id IS NOT NULL uniquement
```
Backfill m7_4a limité aux seeds (51 items human_validated). Items terrain (1438) : item_uid = NULL, item_code = NULL.

Preuve probe : `avec_uid = 1489` reporté dans probe post-m7_4a (mais cette migration n'est pas encore appliquée localement). Données Railway non prouvées.

**Écart au freeze :**  
RÈGLE-29 (freeze) : M6 construit le registre depuis libellés réels. La doctrine identité (item_uid/item_code) aurait dû être définie en M6, pas introduite en M7.4a après 1489 items créés. La couverture item_uid/item_code est partielle : seeds seulement si Railway non prouvé.

**Sévérité :** S2 — dette réelle

**Risque :**  
item_id déterministe = stable. item_uid/item_code partiels = identité composite incomplète. Si une reconstruction requiert item_uid comme ancre, les items terrain sont orphelins d'identité technique.

**Verdict :**  
CANONIQUE pour `item_id` (SHA256 déterministe, non dépendant ordre SQL/batch/LLM).  
NON CANONIQUE pour `item_uid`/`item_code` (couverture partielle, doctrine introduite trop tard).

**Action future requise :**  
ADR doctrine identité item. Backfill item_uid/item_code sur tous les items terrain, ou décision de conserver uniquement item_id comme ancre pérenne.

---

## C. Provenance source

**Objet :**  
Colonne `sources` (JSONB), `dict_version`, `confidence_score` sur `procurement_dict_items`

**Invariant :**  
Chaque item du dictionnaire est rattachable à une source brute réelle M5 (mercurials/IMC) ou à un enrichissement M7 explicitement traçable.

**Preuve brute :**  
`build_dictionary.py` : lit `mercurials.raw_label`, `imc_entries.raw_label`. INSERT avec `sources = '["mercuriale"]'` ou `'["imc"]'`.  
51 items seeds : `sources = '["seed_sahel"]'` (migration m6_dictionary_build).  
Colonne `sources` = JSONB NOT NULL DEFAULT '[]' — présente sur tous les items.

**Écart au freeze :**  
M5 ingestion brute → M6 construction canonique : conforme. La traçabilité est assurée via `sources`. Pas d'item théorique sans origine prouvée dans le flux M5→M6.

**Sévérité :** S1 — écart mineur

**Risque :**  
51 items seeds (`sources = '["seed_sahel"]'`) ont une provenance manuelle non terrain. Ces items existent avant M5. Si une reconstruction "depuis le réel uniquement" est décidée, ces 51 items sont hors scope.

**Verdict :**  
CONFORME pour le flux M5→M6 (mercurials/IMC → dict_items).  
ORPHELINS CONTRÔLÉS pour les 51 seeds (provenance manuelle documentée).

**Action future requise :**  
Aucune action bloquante. Documenter la distinction seeds vs terrain pour la reconstruction.

---

## D. Normalisation

**Objet :**  
Pipeline M5 → M6 : ingestion brute puis normalisation

**Invariant :**  
La normalisation a été faite après ingestion brute. M5 ingère sans corriger la source. M6 construit depuis les libellés réels.

**Preuve brute :**  
`scripts/import_mercuriale.py` : parse HTML/Markdown brut → INSERT dans `mercurials` avec `raw_label` intact.  
`build_dictionary.py` :
```python
def normalize_label(raw: str) -> str:
    # Appel dans build_dictionary APRÈS extraction depuis mercurials
```
La normalisation se fait dans build_dictionary (M6), pas dans l'import mercuriale (M5). Séquence prouvée.

**Écart au freeze :**  
Conforme. M5 = ingestion brute. M6 = normalisation et construction canonique.

**Sévérité :** S0 — conforme

**Risque :**  
Aucun.

**Verdict :**  
CONFORME

**Action future requise :**  
Aucune.

---

## E. Alias

**Objet :**  
`couche_b.procurement_dict_aliases`

**Invariant :**  
Alias = mémoire de variation réelle du terrain, pas cache-misère d'un modèle mal conçu.

**Preuve brute :**  
Migration m6_dictionary_build.py :
```sql
CREATE TABLE IF NOT EXISTS couche_b.dict_proposals (
    id TEXT PRIMARY KEY,
    item_id TEXT REFERENCES couche_b.procurement_dict_items(item_id) ON DELETE RESTRICT,
    proposed_form TEXT NOT NULL,
    ...
)
```
`procurement_dict_aliases` : alias_raw (libellé brut terrain), normalized_alias (UNIQUE), source, confidence.  
`build_dictionary.py` : INSERT alias depuis libellés mercuriale/IMC non mappés sur item existant.  
1596 aliases prouvés (rapport M6). Source = terrain.

**Écart au freeze :**  
Conforme. Les aliases sont construits depuis les libellés réels M5, pas inventés.

**Sévérité :** S0 — conforme

**Risque :**  
Aucun structurel. Le UNIQUE sur normalized_alias empêche les doublons.

**Verdict :**  
CONFORME

**Action future requise :**  
Aucune.

---

## F. Collision

**Objet :**  
`public.dict_collision_log`, RÈGLE-26/27 (fusion auto)

**Invariant :**  
Les fusions automatiques respectent 3 conditions simultanées + enregistrement dans collision_log.

**Preuve brute :**  
Probe : `collision_log M6 : 0 entrées`.  
`build_dictionary.py` : logique collision présente (fonction `log_proposal` si conflit `normalized_alias`). La RÈGLE-26 impose : score ≥ 85 ET category_id ET unit_id. Aucune fusion auto sans ces 3 conditions.  
Zéro entrée collision_log = soit aucune collision rencontrée, soit aucune fusion auto exécutée.

**Écart au freeze :**  
0 entrées collision_log alors que 1596 aliases existent et que le build a traité 1573 libellés bruts. Il est non prouvé que les 3 conditions RÈGLE-26 ont été satisfaites et correctement tracées.

**Sévérité :** S2 — dette réelle contenue

**Risque :**  
Si des fusions ont eu lieu sans collision_log, la traçabilité est absente. Inversement, si aucune fusion n'a eu lieu, le log vide est correct.

**Verdict :**  
NON PROUVÉ — collision_log vide non expliqué. RÈGLE-26/27 non vérifiable sans probe dédiée.

**Action future requise :**  
Probe : compter les cas où normalized_alias existant a été rencontré lors du build. Vérifier si `log_collision` est appelé. Auditer logique build_dictionary sur ce point précis.

---

## G. Taxonomie

**Objet :**  
`couche_b.taxo_l1_domains`, `taxo_l2_families`, `taxo_l3_subfamilies`  
Colonnes `domain_id`, `family_l2_id`, `subfamily_id` sur `procurement_dict_items`

**Invariant :**  
La taxonomie est une couche de classement dérivée du corpus réel. Elle n'est pas un socle artificiel imposé avant l'existence des items.

**Preuve brute :**  
`scripts/seed_taxonomy_v2.py` — structure codée en dur dans le fichier Python :
```python
L1_DATA = [
    ("ALIM_VIVRES", "Alimentation et vivres"),
    ("CARBLUB", "Carburants et lubrifiants"),
    ("TRAVAUXCONST", "Travaux de construction"),
    # ... 15 domaines définis en Python
]
L2_DATA = [
    ("CEREALES_LEG", "ALIM_VIVRES", "Céréales et légumineuses"),
    # ... 57 familles définies en Python
]
# L3 : 155 sous-familles définies en Python
```
Ces IDs et labels sont inventés par le développeur, pas extraits du corpus.  
Probe post-seed : taxo_l3_subfamilies = 23 (≠ 155 annoncés). Soit seed non exécuté complètement, soit fichier modifié.  
Phase A classification LLM : 77.9% flagged → le LLM invente des codes L3 (`cafe`, `lait`, `farine`) non présents dans la DB. Preuve que la taxonomie DB est insuffisante pour couvrir le corpus réel.

**Écart au freeze :**  
Doctrine freeze : "le système s'adapte au réel ; il ne corrige pas la source." La taxonomie prédéfinie fait l'inverse : elle impose le cadre d'abord. M7.2 est introduit AVANT la classification du corpus → taxonomie imaginée avant corpus.

**Sévérité :** S3 — dérive active

**Risque :**  
Taxonomie incompatible avec le corpus réel (77.9% d'échec prouvé). Toute reconstruction depuis le réel produira des items que la taxonomie actuelle ne peut pas classer correctement.

**Verdict :**  
DÉRIVE ACTIVE — taxonomie prédéfinie, pas construite depuis les libellés réels du corpus

**Action future requise :**  
ADR obligatoire : décider entre (1) reconstruire la taxonomie par induction depuis le corpus, ou (2) étendre la taxonomie actuelle pour couvrir les items terrain non classifiables. Interdire seed_taxonomy_v2.py sans révision.

---

## H. Enrichissement M7

**Objet :**  
Périmètre de M7 vs fondation M6

**Invariant :**  
M7 enrichit M6. M7 ne remplace pas, ne refonde pas, ne crée pas de structure amont.

**Preuve brute :**  
M7.2 (m7_2_taxonomy_reset.py) : crée taxo_l1/l2/l3 + ajoute colonnes structurelles sur procurement_dict_items (domain_id, family_l2_id, subfamily_id, taxo_version, taxo_validated, taxo_validated_by, taxo_validated_at).  
M7.3 (m7_3_dict_nerve_center.py) : crée dict_price_references, dict_uom_conversions, dgmp_thresholds, dict_item_suppliers. Ajoute colonnes item_type, default_uom, default_currency, unspsc_code, classification_confidence, classification_source, needs_review, quality_score, last_hash. Crée 3 triggers.  
M7.4a (m7_4a_item_identity_doctrine.py) : ajoute item_uid, item_code, birth_domain_id, birth_family_l2_id, birth_subfamily_id, id_version, llm_*_raw.  

La doctrine identité item (item_uid/item_code/birth_*) est introduite en M7.4a, soit après que 1489 items existent déjà sans cette doctrine.

**Écart au freeze :**  
M7 a introduit : (1) la structure taxonomique du dictionnaire (colonnes FK sur procurement_dict_items), (2) la doctrine identité item, (3) l'infrastructure nerve center. Ces trois éléments sont de la fondation, pas de l'enrichissement. Ils auraient dû être définis en M6.

**Sévérité :** S3 — dérive active

**Risque :**  
Si M6 est rejoué depuis zéro, les structures introduites par M7.2-M7.4a sont des prérequis non documentés. Le dictionnaire M6 ne peut pas fonctionner complètement sans les colonnes M7.

**Verdict :**  
USURPATION PARTIELLE — M7 a fait le travail de M6 sur trois points (taxonomie, identité, nerve center)

**Action future requise :**  
ADR délimitation M6/M7. Si reconstruction : décider quel schéma appartient à M6 et lequel à M7. Interdire toute nouvelle colonne structurelle en M7 sans mandat explicite.

---

## I. FK / delete rules

**Objet :**  
FKs entre `procurement_dict_items` et les tables taxonomiques

**Invariant :**  
Les FKs protègent le registre. Aucune cascade depuis la taxonomie vers le dictionnaire.

**Preuve brute :**  
Migration m7_2_taxonomy_reset.py — colonnes ajoutées avec `REFERENCES ... (domain_id)` sans `ON DELETE` spécifié.  
PostgreSQL défaut = `NO ACTION` : le DELETE sur taxo_l1_domains échoue si des items le référencent.  
Migration m7_3_dict_nerve_center.py — dict_price_references : `ON DELETE RESTRICT`.  
Migration m6_dictionary_build.py — dict_proposals : `ON DELETE RESTRICT`.  
Migration m7_2 — taxo_l2_families : `ON DELETE RESTRICT`. taxo_l3_subfamilies : `ON DELETE RESTRICT`.

Aucun `ON DELETE CASCADE` vers procurement_dict_items identifié dans les migrations lues.

**Écart au freeze :**  
Conforme. Le registre ne peut pas être détruit par une opération taxonomique.

**Sévérité :** S0 — conforme

**Risque :**  
Aucun risque de destruction cascade. Risque inverse : DELETE taxonomie bloqué si items existent → prévisible et acceptable.

**Verdict :**  
CONFORME — FKs protègent le registre, aucun CASCADE toxique identifié

**Action future requise :**  
Aucune.

---

## J. Scripts

**Objet :**  
`scripts/build_dictionary.py`, `scripts/etl_vendors_wave2.py`, `scripts/seed_taxonomy_v2.py`, `scripts/classify_taxonomy_v2.py`, `scripts/m7_rebuild_t0_purge.py`

**Invariant :**  
Chaque script est strictement borné à son rôle milestone. Il ne lit/écrit pas hors périmètre. Il ne peut pas tuer des données sans garde-fou.

**Preuve brute — build_dictionary.py :**  
Lit : `couche_b.mercurials`, `couche_b.imc_entries`, `couche_b.procurement_dict_items` (slugs existants), `public.dict_collision_log` schema, `couche_b.dict_proposals` schema.  
Écrit : `couche_b.procurement_dict_items`, `couche_b.procurement_dict_aliases`, `couche_b.dict_proposals`.  
Mode dry-run présent (`--dry-run`). Borné M6. MODIFIÉ non commité.

**Preuve brute — etl_vendors_wave2.py :**  
Lit/écrit : tables `vendors`. MODIFIÉ non commité. Périmètre M4.

**Preuve brute — seed_taxonomy_v2.py :**  
Lit : DB pour vérifier existant. Écrit : `couche_b.taxo_l1_domains`, `taxo_l2_families`, `taxo_l3_subfamilies` via INSERT … ON CONFLICT DO NOTHING.  
Structure L1/L2/L3 codée en dur dans le fichier. MODIFIÉ non commité. Commentaire : "ce script INSERT, le code CHARGE depuis DB. Après insertion, la DB est source de vérité."

**Preuve brute — classify_taxonomy_v2.py :**  
Lit : `couche_b.taxo_l1_domains/l2/l3`, `couche_b.procurement_dict_items` (sans domain_id).  
Écrit : `couche_b.taxo_proposals_v2` uniquement (RÈGLE-V1 — jamais UPDATE dict_items direct).  
Mode dry-run présent (`--dry-run`). Appels LLM Mistral. Phase A : 77.9% flagged.

**Preuve brute — m7_rebuild_t0_purge.py :**  
```python
conn.execute("TRUNCATE couche_b.taxo_proposals_v2")  # T0-A
conn.execute("UPDATE couche_b.procurement_dict_items SET domain_id=NULL, family_l2_id=NULL, subfamily_id=NULL")  # T0-C
conn.execute("UPDATE couche_b.procurement_dict_items SET taxo_version=NULL, ...")  # T0-C bis
conn.execute("DELETE FROM couche_b.taxo_l3_subfamilies")  # T0-B
conn.execute("DELETE FROM couche_b.taxo_l2_families")     # T0-B
conn.execute("DELETE FROM couche_b.taxo_l1_domains")      # T0-B
```
**Aucun paramètre `--dry-run` dans le code lu. Aucune confirmation interactive. Exécution directe en production.**  
Garde post : vérifie seeds==51 et avec_uid==1489. Si non conforme : sys.exit(1). Mais la purge est déjà exécutée à ce stade.

**Écart au freeze :**  
m7_rebuild_t0_purge.py : script destructif sans mode sûr. Contraire à la doctrine "les imperfections sont tracées, pas cachées."  
classify_taxonomy_v2.py : 77.9% échec prouvé. Script malade.  
build_dictionary.py, etl_vendors_wave2.py, seed_taxonomy_v2.py : modifiés non commités = périmètre non auditable.

**Sévérité :** S4 pour m7_rebuild_t0_purge.py — destruction potentielle  
S3 pour classify_taxonomy_v2.py — dérive active  
S2 pour les 3 scripts modifiés non commités

**Risque :**  
m7_rebuild_t0_purge.py : exécution accidentelle = perte totale taxonomie + reset classification 1489 items.  
classify_taxonomy_v2.py : reclassification LLM avec taxonomie incomplète → pollution taxo_proposals_v2.

**Verdict :**  
`m7_rebuild_t0_purge.py` — À INTERDIRE IMMÉDIATEMENT (aucun garde-fou, destructif)  
`classify_taxonomy_v2.py` — MALADE (résultats prouvés incompatibles avec corpus)  
`build_dictionary.py`, `etl_vendors_wave2.py`, `seed_taxonomy_v2.py` — SUSPECTS (modifiés non commités, périmètre non prouvable)

**Action future requise :**  
Interdire m7_rebuild_t0_purge.py sans dry-run et confirmation. ADR avant toute nouvelle exécution. Auditer les 3 scripts modifiés (diff) avant merge.

---

## K. Repo / DB / prod truth

**Objet :**  
Alignement repo ↔ DB locale ↔ Railway

**Invariant :**  
Les trois vérités sont alignées. Aucun mismatch.

**Preuve brute :**  
- alembic heads (repo) : `m7_4a_item_identity_doctrine`  
- alembic current (local) : `m7_4_dict_vivant`  
- Railway : NON PROUVÉ  
- Tags M7.4/M7.4a : absents  
- Milestone M7.4a "done" : non déclaré, non taggé

**Écart au freeze :**  
DB locale en retard d'une migration. Railway non auditable. Le milestone M7.4a est dans le repo mais non appliqué localement. Toute déclaration "M7.4a done" serait un mensonge système.

**Sévérité :** S2 — dérive réelle contenue (local)  
S3 pour Railway si diverge — NON PROUVÉ donc classé anomalie hostile

**Risque :**  
Si Railway a m7_4_dict_vivant mais pas m7_4a → divergence repo/prod. Si Railway a une version antérieure → divergence structurelle majeure.

**Verdict :**  
INCOHÉRENT — local ≠ head. Railway = anomalie hostile (non prouvé = faux par axiome d'audit)

**Action future requise :**  
Probe Railway : `alembic current` contre Railway DATABASE_URL. Probe counts Railway. Aligner avant toute déclaration "done".
