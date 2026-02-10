a) Principe

Couche A = traitement procurement

Couche B = mémoire marché append-only

A et B sont faiblement couplées par API uniquement

b) A → B (WRITE)

Autorisé :

POST /api/market-signals

Uniquement après validation comité

Append-only

Données autorisées :

vendor_name
item_description
unit_text
location_name
unit_price
currency
observation_date
source_ref
confidence

Interdit :

UPDATE

DELETE

accès DB direct

création catalogues sans validation

c) B → A (READ)

Autorisé :

GET /api/catalog/*/search

GET /api/market-intelligence/stats

Interdit :

push B → A

callbacks

accès documents/offres

d) Sanctions

Toute violation = bug critique bloquant release.
