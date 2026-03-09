# ADR-MRD2-GENETIC
# ADR Génétique — Registre canonique DMS
# Date     : 2026-03-09
# Décideur : AO — Abdoulaye Ousmane
# Statut   : ACCEPTÉ — FREEZE
# Milestone: MRD-2

---

## Contexte

Le segment M4→M7 a subi des dérives causées par une confusion
entre registre (mémoire terrain) et taxonomie (classification).
Ce document grave les définitions et interdits qui rendent
cette confusion physiquement impossible dans le code.

---

## SECTION A — 8 DÉFINITIONS CANONIQUES

### DEF-01 — item canonique

Un item canonique est l'unité atomique du registre.
Il existe indépendamment de toute taxonomie.
Son identité est définie par son fingerprint, jamais par son
placement dans un arbre de classification.

### DEF-02 — fingerprint

fingerprint = sha256(normalize(label) + "|" + source_type + "|" + source_id)
normalize() = strip + lower + collapse_whitespace

Le fingerprint est immuable après création.
Deux items de même fingerprint = collision → tracée dans dict_collision_log.
Jamais de DELETE + re-INSERT pour "corriger" un fingerprint.

### DEF-03 — registre

Le registre est la table procurement_dict_items.
Il est append-only + UPSERT fingerprint.
Jamais DELETE. Jamais TRUNCATE. Jamais DROP + recreate.
Un item désactivé reste dans le registre avec active=FALSE.

### DEF-04 — alias

Un alias est la mémoire d'un libellé terrain.
Il est préservé à vie dans procurement_dict_aliases.
Supprimer un alias = perte irréversible de mémoire terrain.
ON DELETE RESTRICT obligatoire sur la FK aliases → items.

### DEF-05 — taxonomie

La taxonomie est une couche DÉRIVÉE du registre.
Elle est construite APRÈS que les items existent.
Elle ne fonde jamais l'identité d'un item.
Un item sans taxonomie est valide.
Une taxonomie sans item correspondant dans le registre est invalide.

### DEF-06 — proposal

Un proposal est une suggestion de classification LLM ou système.
Il requiert une validation humaine (human_validated=TRUE) avant
d'être considéré comme canonique.
Les proposals sont append-only dans taxo_proposals_v2.

### DEF-07 — birth_source

birth_source identifie l'origine d'un item :
  mercuriale | imc | seed | terrain
Il est immuable après création (jamais UPDATE).
Il permet de tracer la lignée de tout item.

### DEF-08 — collision

Une collision est l'état où deux sources différentes produisent
le même fingerprint pour des items distincts.
Toute collision est tracée dans dict_collision_log.
Elle ne cause jamais de STOP — elle est documentée et auditée.

---

## SECTION B — 8 INTERDITS STRUCTURELS (IS-01 / IS-08)

### IS-01 — Interdit : DELETE sur tables mémoire terrain

Interdit : DELETE FROM procurement_dict_items
Interdit : DELETE FROM procurement_dict_aliases
Interdit : TRUNCATE TABLE procurement_dict_items
Interdit : DROP TABLE procurement_dict_items
Seule exception : active=FALSE pour désactivation logique.
Violation → STOP-06 (destructive_loss > 0).

### IS-02 — Interdit : CASCADE FK sur tables mémoire terrain

Interdit : ON DELETE CASCADE sur FK pointant vers
           procurement_dict_items ou procurement_dict_aliases.
Obligatoire : ON DELETE RESTRICT ou ON DELETE NO ACTION.
Violation → STOP-14 (CASCADE FK détectée couche_b).
MRD-3 a corrigé cette violation pour les aliases.

### IS-03 — Interdit : taxonomie comme fondation d'identité

Interdit : utiliser domain_id, family_l2_id ou subfamily_id
           comme clé primaire ou identifiant unique d'un item.
Ces colonnes sont dérivées. Elles peuvent être nulles.
Un item NULL sur toutes les colonnes taxonomiques est valide.
Violation → STOP-07 (taxonomie réintroduite avant fin MRD-4).

### IS-04 — Interdit : LLM sans liste fermée

Interdit : laisser un LLM assigner librement domain_id ou
           family_l2_id sans validation contre une liste fermée.
Obligatoire : vérifier que la valeur proposée existe dans
              taxo_l1_domains ou taxo_l2_families avant commit.
Items non résolus → champ UNRESOLVED documenté.
Violation → STOP-10 (LLM hors liste fermée sans UNRESOLVED).

### IS-05 — Interdit : migration sans downgrade() testé

Interdit : merger une migration Alembic dont le downgrade()
           échoue ou est un simple pass sans logique réelle.
Obligatoire : cycle upgrade → test → downgrade → upgrade → test
              avant tout merge.
Violation → STOP-09 (downgrade() échoue ou absent).
DEF-MRD3-03 était cette violation — corrigée MRD-4.

### IS-06 — Interdit : alembic heads > 1

Interdit : tout état où alembic heads retourne > 1 ligne.
Obligatoire : merge-head migration si > 1 head détecté.
Violation → STOP-01 (alembic heads > 1 ligne).

### IS-07 — Interdit : DATABASE_URL Railway en local

Interdit : utiliser une DATABASE_URL pointant Railway
           pour exécuter des migrations ou des tests locaux.
Obligatoire : guard CONTRACT-02 dans tout script.
  if 'railway' in os.environ.get('DATABASE_URL','').lower():
      raise SystemExit('CONTRACT-02 VIOLE')
Violation → STOP-12 (DATABASE_URL contient railway).

### IS-08 — Interdit : milestone sauté ou parallèle

Interdit : démarrer MRD-N si next_milestone != MRD-N
           dans MRD_CURRENT_STATE.md.
Interdit : deux agents sur le même milestone simultanément.
Obligatoire : vérifier CONTRACT-04 via validate_mrd_state.py.
Violation → STOP-02 (next_milestone != mandat reçu).

---

## SECTION C — DÉFAILLANCES MRD-3 ET CORRECTIONS

Les défaillances suivantes ont été mergées en MRD-3.
Elles violent les interdits ci-dessus.
Elles sont corrigées dans MRD-4.

| Défaillance  | Interdit violé | Correction MRD-4              |
|--------------|----------------|-------------------------------|
| DEF-MRD3-01  | IS-06          | Numérotation migration clean  |
| DEF-MRD3-02  | IS-06          | Cycle alembic current intégré |
| DEF-MRD3-03  | IS-05          | downgrade() fail-loud testé   |
| DEF-MRD3-04  | IS-06          | Tests head dynamiques         |
| DEF-MRD3-05  | IS-01/IS-03    | Colonne fingerprint créée     |
| DEF-MRD3-06  | IS-01/IS-02    | Triggers protection créés     |

---

## Conséquences

Tout code qui viole un IS-* est bloqué en CI.
Tout agent qui produit une violation IS-* documente une défaillance DEF-MRD{N}-0N.
Tout merge avec une violation non documentée est interdit.
