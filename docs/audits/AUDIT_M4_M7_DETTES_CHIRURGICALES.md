# AUDIT M4→M7 — DETTES CHIRURGICALES

**Date :** 2026-03-08  
**Sources :** TECHNICAL_DEBT.md, HANDOVER_AGENT.md, ADR-0016, mandats M7.4, probes brutes  
**Référence :** DMS V4.1.0 FREEZE DÉFINITIF

---

## TABLE DETTES M4→M7

| ID | Dette | Source | Milestone origine | Nature | Sévérité | Impact système | Bloque reconstruction | Type solde |
|----|-------|--------|-------------------|--------|----------|----------------|----------------------|------------|
| D-01 | Freeze Partie XI obsolète — noms 039/041 inexistants | DMS_V4.1.0_FREEZE.md | Antérieur M4 | Référence fausse | **S4** | Toute décision basée sur le freeze est non fiable | **OUI** | probe + ADR |
| D-02 | DB locale en retard sur head (m7_4 ≠ m7_4a) | alembic current | M7.4a | Dérive alembic | S2 | Local non aligné avec repo | NON | migration |
| D-03 | m7_rebuild_t0_purge.py sans dry-run ni garde-fou | scripts/ | M7.4 | Script destructif non sécurisé | **S4** | TRUNCATE + DELETE taxo + NULL domain_id sur 1489 items | **OUI** | interdiction script |
| D-04 | Taxonomie L1/L2/L3 prédéfinie (15/57/155) avant corpus | m7_2_taxonomy_reset | M7.2 | Doctrine inversée | **S3** | Phase A : 77.9% flagged. Taxonomie incompatible corpus. | **OUI** | ADR + rebuild taxo |
| D-05 | M7 usurpe fondation M6 — colonnes structurelles sur dict_items | m7_2, m7_3, m7_4a | M7.2–M7.4a | Périmètre dérivant | **S3** | M6 non rejouable sans prérequis M7 | **OUI** | dépréciation + ADR |
| D-06 | item_uid/item_code couverture partielle (seeds seulement) | m7_4a | M7.4a | Doctrine identité incomplète | S2 | 1438 items terrain sans ancre technique | NON | rebuild ou ADR |
| D-07 | collision_log M6 = 0 entrées (RÈGLE-26/27 non prouvée) | probe | M6 | Invariant non vérifiable | S2 | Traçabilité fusions absente | NON | probe |
| D-08 | Double préfixe 040 (040_geo_master_mali + 040_mercuriale_ingest) | alembic/versions/ | M3/M5 | Convention nommage cassée | S1 | Confusion lecture humaine | NON | ADR nommage |
| D-09 | taxo_l3_subfamilies = 23 (seed annonce 155, probe dit 23) | probe_post.txt | M7.2 | Seed partiel ou modifié | **S3** | Taxonomie L3 insuffisante pour 1484 items | **OUI** | probe + correction |
| D-10 | Phase A classification LLM : 77.9% flagged | HANDOVER_M74_PHASE_A | M7.4 | Échec prouvé | S3 | taxo_proposals_v2 polluée (834 flagged) | OUI (si replay) | probe + rebuild taxo |
| D-11 | feat/m7-rebuild-dict-from-terrain : 5 fichiers modifiés non commités | git status | M7.4 | Working tree sale | S2 | build_dictionary, etl_vendors, seed_taxonomy non auditables | NON | commit ou revert |
| D-12 | Aucun tag M7.4 / M7.4a (milestones non déclarés done) | git log | M7.4/M7.4a | Milestone non prouvé done | S2 | État M7.4a inconnu en prod | NON | probe Railway |
| D-13 | Railway non prouvé (aucun accès confirmé) | probe | — | Vérité prod inconnue | S3 | Tout compte Railway = non prouvé = faux | OUI | probe Railway |
| D-14 | TD-009 chaîne Alembic hors convention 0NN_ | TECHNICAL_DEBT | M5-PRE | Convention nommage | S1 | Risque ambiguïté future | NON | ADR |
| D-15 | TD-001 vendor_id MAX()+1 non atomique | TECHNICAL_DEBT | M4 | Séquence non atomique | S2 | Collision import parallèle possible | NON | migration |
| D-16 | Trigger fn_compute_quality_score couplé à domain_id | m7_3, m7_4 | M7.3 | Couplage taxonomie↔qualité dans trigger | S2 | Items sans taxo pénalisés qualitativement | NON | ADR |
| D-17 | DETTE-M1-04 role_id legacy DROP bloqué (7 usages runtime) | TECHNICAL_DEBT | M2 | Dette schéma non soldée | S2 | Colonne zombie active | NON | migration |

---

## DETTES S4 — DESTRUCTION POTENTIELLE / MENSONGE SYSTÈME

### D-01 — Freeze Partie XI obsolète

**Objet :**  
DMS_V4.1.0_FREEZE.md Partie XI annonce :
- M4 head = `039_seed_vendors_mali` → ABSENT du repo
- M6 head = `041_procurement_dictionary` → ABSENT du repo (041 = vendor_identities = M4)

**Preuve brute :**  
Lecture `alembic/versions/` : aucun fichier `039_seed_vendors_mali.py`. Aucun fichier `041_procurement_dictionary.py`.

**Impact :**  
Le freeze, censé être la "référence supérieure" et le "plan directeur unique", contient des noms de migration qui n'existent pas. Toute décision de reconstruction basée sur ce freeze sans correction préalable est construite sur une fondation fausse.

**Sévérité :** S4 — corruption d'invariant (la référence est le freeze, et le freeze est faux)

**Verdict :** MENSONGE SYSTÈME — table Partie XI invalide

**Action :** Probe : identifier la version réelle du freeze. Reconstruire la table de vérité migrations. Mettre à jour le freeze ou créer un document de substitution.

---

### D-03 — m7_rebuild_t0_purge.py sans garde-fou

**Objet :**  
`scripts/m7_rebuild_t0_purge.py`

**Preuve brute :**  
```python
# Aucun argparse. Aucun --dry-run. Aucune confirmation interactive.
conn.execute("TRUNCATE couche_b.taxo_proposals_v2")
conn.execute("UPDATE couche_b.procurement_dict_items SET domain_id=NULL, family_l2_id=NULL, subfamily_id=NULL")
conn.execute("DELETE FROM couche_b.taxo_l3_subfamilies")
conn.execute("DELETE FROM couche_b.taxo_l2_families")
conn.execute("DELETE FROM couche_b.taxo_l1_domains")
```
Le script exécute la purge en une transaction. La seule "garde" est une vérification post-purge (seeds==51, uid==1489). Si cette vérification échoue, `sys.exit(1)` est appelé mais la purge est déjà commise.

**Impact :**  
Exécution accidentelle sur Railway = destruction totale de :
- Toute la taxonomie L1/L2/L3 (DELETE)
- Toutes les propositions LLM (TRUNCATE)
- Classification de 1489 items (domain_id=NULL)

**Sévérité :** S4 — destruction potentielle

**Verdict :** À INTERDIRE IMMÉDIATEMENT

**Action :** Interdire l'exécution sans : (1) flag `--confirm` explicite, (2) dry-run obligatoire préalable, (3) backup Railway vérifié. ADR "mandat purge M7" requis avant toute réexécution.

---

## DETTES S3 — DÉRIVE ACTIVE

### D-04 — Taxonomie prédéfinie avant corpus

**Objet :**  
`scripts/seed_taxonomy_v2.py` + migration `m7_2_taxonomy_reset.py`

**Preuve brute :**  
```python
# seed_taxonomy_v2.py — structure inventée en Python
L1_DATA = [("ALIM_VIVRES", "Alimentation et vivres"), ...]  # 15 domaines
L2_DATA = [("CEREALES_LEG", "ALIM_VIVRES", "Céréales et légumineuses"), ...]  # 57 familles
# L3 : 155 sous-familles
```
Probe post-seed : taxo_l3_subfamilies = 23 en base (≠ 155).  
Phase A LLM : 77.9% flagged — le LLM invente des codes L3 inexistants.

**Impact :**  
La doctrine freeze impose "le système s'adapte au réel". La taxonomie fait l'inverse. Elle a été conçue en dehors du corpus, imposée en M7.2, et a produit un taux d'échec de 77.9% lors de la classification automatique.

**Sévérité :** S3 — dérive active

**Verdict :** DÉRIVE ACTIVE — bloque reconstruction propre

**Action :** ADR taxo-dérivée vs taxo-imposée. Si reconstruction : construire taxonomie par induction depuis le corpus réel (clustering libellés mercurials/IMC), pas par décision a priori.

---

### D-05 — M7 usurpe fondation M6

**Objet :**  
Colonnes structurelles sur `procurement_dict_items` introduites par M7.2, M7.3, M7.4a

**Preuve brute :**  
- M7.2 : +7 colonnes (domain_id, family_l2_id, subfamily_id, taxo_version, taxo_validated, taxo_validated_by, taxo_validated_at)
- M7.3 : +7 colonnes (item_type, default_uom, default_currency, unspsc_code, classification_confidence, classification_source, needs_review, quality_score, last_hash)
- M7.4a : +9 colonnes (item_uid, item_code, birth_domain_id, birth_family_l2_id, birth_subfamily_id, id_version, llm_domain_id_raw, llm_family_l2_id_raw, llm_subfamily_id_raw)

Au total M7 a ajouté **23 colonnes structurelles** sur la table cœur du dictionnaire (procurement_dict_items), qui ne contenait que les colonnes M6 + les colonnes pre-M6 (family_id legacy, label_fr, label_en, default_unit, active, canonical_slug, dict_version, confidence_score, human_validated, sources, last_seen, updated_at).

**Impact :**  
Si M6 doit être rejoué depuis zéro, il manque 23 colonnes qui sont dans M7. Le dictionnaire M6 ne peut pas fonctionner sans ses colonnes M7. La frontière M6/M7 est effacée.

**Sévérité :** S3 — dérive active

**Verdict :** DÉRIVE ACTIVE — bloque reconstruction M6 standalone

**Action :** ADR "périmètre schéma M6 vs M7". Documenter quelles colonnes appartiennent à quel milestone. Décider si les colonnes M7.2-M7.4a sont promus en M6 lors de la reconstruction.

---

### D-09 — taxo_l3_subfamilies = 23 (annoncé 155)

**Objet :**  
`couche_b.taxo_l3_subfamilies` — count réel vs attendu

**Preuve brute :**  
probe_post.txt : `taxo_l3_subfamilies = 23 ⚠ 23 < 50`  
seed_taxonomy_v2.py (version précédente) : 155 sous-familles définies.  
seed_taxonomy_v2.py est dans la liste des fichiers **modifiés non commités** (git status).

**Cause probable :**  
seed_taxonomy_v2.py a été modifié depuis son état d'origine. La version modifiée insère un sous-ensemble réduit de L3. La discordance entre 23 (DB) et 155 (code annoncé) est prouvée.

**Impact :**  
Taxonomie L3 insuffisante = LLM ne peut pas classer correctement = Phase A 77.9% flagged.

**Sévérité :** S3 — dérive active

**Verdict :** DÉRIVE ACTIVE — cause directe de l'échec Phase A

**Action :** Probe : lire la version actuelle (modifiée) de seed_taxonomy_v2.py. Comparer avec la version committée. Déterminer si la réduction L3 est volontaire ou accidentelle.

---

### D-13 — Railway non prouvé

**Objet :**  
État de la base de données Railway

**Preuve brute :**  
Aucun output Railway confirmé dans les probes. Les fichiers alembic_m74.txt contiennent uniquement des messages INFO Alembic sans count ni version. Aucune preuve que m7_4 ou m7_4a est appliqué sur Railway.

**Impact :**  
L'état réel de la production est inconnu. Milestones M7.4/M7.4a potentiellement non appliqués en prod. Données Railway potentiellement différentes de local.

**Sévérité :** S3 — anomalie hostile (non prouvé = faux par axiome d'audit)

**Verdict :** NON PROUVÉ — Railway = orphelin de vérité

**Action :** Probe Railway : `alembic current`, counts procurement_dict_items, taxo L1/L2/L3, taxo_proposals_v2.

---

## DETTES S2 — RÉELLES CONTENUES

### D-02 — DB locale en retard

**Objet :** alembic current local = m7_4_dict_vivant ≠ head m7_4a

**Action :** `alembic upgrade head` sur DB locale après vérification Railway.

---

### D-06 — item_uid/item_code couverture partielle

**Objet :** 1438 items terrain sans item_uid ni item_code

**Action :** ADR doctrine identité. Décider si item_id (SHA256) suffit comme ancre unique ou si item_uid/item_code doivent être backfillés sur tous les items.

---

### D-07 — collision_log M6 = 0

**Objet :** dict_collision_log vide alors que 1573 libellés bruts traités

**Action :** Probe : relire build_dictionary.py sur la logique de collision. Vérifier si `log_collision` est appelé. Exécuter dry-run avec comptage collisions détectées.

---

### D-11 — Working tree sale

**Objet :** build_dictionary.py, etl_vendors_wave2.py, seed_taxonomy_v2.py, tests modifiés non commités

**Action :** Diff des 5 fichiers. Commiter les modifications légitimes. Reverter les modifications hors scope.

---

### D-12 — Milestones M7.4/M7.4a non taggés

**Objet :** Aucun tag v4.x.x-m7.4-done ni v4.x.x-m7.4a-done

**Action :** Ne pas tagger sans probe Railway confirmé et alembic current = m7_4a en prod.

---

## CLASSEMENT PAR PRIORITÉ DE SOLDE

| Priorité | Dette | Type solde | Condition |
|----------|-------|------------|-----------|
| 1 | D-03 — m7_rebuild_t0_purge.py | Interdiction immédiate | Sans condition — script destructif non sécurisé |
| 2 | D-13 — Railway non prouvé | Probe | Accès DATABASE_URL Railway + alembic current |
| 3 | D-01 — Freeze obsolète | ADR / document | Reconstruire table vérité migrations |
| 4 | D-09 — taxo_l3 = 23 vs 155 | Probe + diff | Lire seed_taxonomy_v2.py modifié |
| 5 | D-11 — Working tree sale | commit/revert | Diff 5 fichiers modifiés |
| 6 | D-04 — Taxonomie prédéfinie | ADR | Décision doctrine taxo-dérivée vs taxo-imposée |
| 7 | D-05 — M7 usurpe M6 | ADR | Décision périmètre M6/M7 pour reconstruction |
| 8 | D-02 — DB locale retard | migration | `alembic upgrade head` post-probe Railway |
| 9 | D-10 — Phase A 77.9% flagged | probe + rebuild | Après D-04 résolu |
| 10 | D-06 — item_uid partiel | ADR | Après D-05 résolu |
| 11+ | D-07, D-08, D-14→D-17 | probe/ADR | Non bloquants |
