CONTRAT FRONTIÈRE A/B — COUPLAGE FAIBLE PAR API (OPPOSABLE · FREEZABLE)

Statut : CANONIQUE · OPPOSABLE · FREEZABLE
Version : V3.3.2
Portée : Toute implémentation Couche A et Couche B, y compris tests CI et déploiement

A) Principe (définition non ambiguë)

Couche A = traitement procurement (moteur d’exécution)

Ingestion, extraction, normalisation, scoring, génération CBA/PV, gestion du comité, registre de dépôt, traçabilité du process d’achat.

Couche B = mémoire marché append-only (market intelligence)

Stockage et restitution du contexte marché : mercuriale, historique, surveys, signaux consolidés.

La mémoire est non prescriptive : elle informe, n’ordonne pas.

Couplage faible obligatoire

Couche A et Couche B communiquent exclusivement par API HTTP.

Interdiction absolue de couplage par :

accès DB direct inter-couche,

partage de schémas internes comme dépendance runtime,

import de modules Couche B dans Couche A (et inversement),

accès aux tables Couche A depuis le code Couche B (et inversement).

B) A → B (WRITE) — Écriture autorisée, bornée, append-only
B.1 Condition d’autorisation (gate comité)

Autorisé uniquement après validation comité (case validé, comité LOCK + décision enregistrée).

Toute tentative d’écriture A → B avant validation comité = refusée (HTTP 403 ou 409 selon convention).

Le mécanisme d’autorisation doit être testable (tests d’intégration).

B.2 Endpoint autorisé (unique)

Autorisé :

POST /api/market-signals

Interdit :

Tout autre endpoint d’écriture A → B (y compris “admin import” non documenté).

B.3 Règles append-only (opposables)

Interdit : UPDATE sur les enregistrements de signaux marché

Interdit : DELETE sur les enregistrements de signaux marché

Autorisé : INSERT uniquement (append-only)

Interdictions structurelles :

Interdit : accès DB direct A → tables Couche B

Interdit : scripts “backdoor” non versionnés

Interdit : création de catalogues / référentiels marché sans validation humaine (voir B.6)

B.4 Données autorisées (whitelist stricte)

Le payload de POST /api/market-signals est strictement limité aux champs suivants :

vendor_name

item_description

unit_text

location_name

unit_price

currency

observation_date

source_ref

confidence

Tout champ hors whitelist :

soit est rejeté (HTTP 400),

soit est ignoré explicitement (mais la règle recommandée est rejet, pour éviter la dérive silencieuse).

B.5 Règles de traçabilité minimales

Chaque écriture A → B doit produire :

une entrée audit_log côté A (action “market_signal_publish”),

une entrée append-only côté B (event ou audit interne),

un lien non ambigu vers le case_id/référence décision (via source_ref ou champ internal id si autorisé par le modèle — mais dans ce contrat on ne rajoute pas de champ, donc source_ref doit porter le lien).

B.6 Interdiction de “catalogues” non validés

Interdit :

création automatique d’un catalogue marché “canonique” à partir de données brutes,

consolidation ou normalisation “silencieuse” sans validation.

Règle :

toute consolidation structurante (catalogue, dictionnaire marché, item canonique) doit être une fonctionnalité explicite, versionnée, testée, et soumise aux règles de validation humaine définies par la Constitution.

C) B → A (READ) — Lecture autorisée, bornée, pull-only
C.1 Endpoints autorisés (liste fermée)

Autorisé :

GET /api/catalog/*/search

GET /api/market-intelligence/stats

Tout autre endpoint B → A doit être documenté et approuvé par ADR avant existence.

C.2 Interdictions de flux (push interdit)

Interdit :

push B → A

callbacks

webhooks

“suggestions temps réel” injectées dans A

tout mécanisme d’influence active de A par B

Le modèle autorisé est : A interroge (pull), B répond.

C.3 Interdiction d’accès aux données Couche A

Interdit à Couche B (même en lecture) :

accès aux documents,

accès aux offres,

accès aux extractions,

accès aux critères/scoring en cours,

accès au registre dépôt,

accès à toute table/processus Couche A.

La Couche B ne voit que ce qui lui est publié via A → B après validation comité, et ses propres sources (mercuriale, surveys, historique).

D) Sanctions (niveau release)

Toute violation du présent contrat = BUG CRITIQUE

Bloque la release.

Bloque le merge (CI doit échouer si la violation est détectable).

Exemples de violations critiques

DB direct A↔B

UPDATE/DELETE sur données append-only

Écriture A→B avant validation comité

Push/callback B→A

Couche B lisant documents/offres/extractions

Ajout de champs hors whitelist dans POST /api/market-signals

Enforcement requis

Tests CI dédiés (statique + intégration) doivent exister pour détecter :

imports interdits,

endpoints non autorisés,

tentatives UPDATE/DELETE,

publication avant validation comité.

FIN — CONTRAT FRONTIÈRE A/B (OPPOSABLE · FREEZABLE)
