# M12 Framework Calibration

## Framework Detection — bootstrap_75

| Metrique | Valeur |
|----------|--------|
| Accuracy globale | 0.8649 |
| Total evaluable | 74 / 75 |
| Seuil requis | >= 0.85 |
| Resultat | PASS |

## Distribution framework detectee

| Framework | Count | % |
|-----------|-------|---|
| sci | 52 | 69.3% |
| mixed | 10 | 13.3% |
| unknown | 10 | 13.3% |
| world_bank | 2 | 2.7% |
| bad | 1 | 1.3% |

## Interpretation

Le corpus est fortement oriente SCI Mali (69.3%), ce qui est coherent avec
le contexte operationnel (Save the Children International Mali).

Les 10 cas `mixed` correspondent a des documents ou des signaux de
plusieurs frameworks coexistent (ex: document SCI referencant des
procedures DGMP Mali ou World Bank).

Les 10 cas `unknown` correspondent a des documents sans signaux framework
forts (CVs, fiches signaletiques, documents generiques).

## Configuration framework_thresholds.yaml

Le fichier `config/framework_thresholds.yaml` definit les seuils de
decision pour la detection framework :

- `min_score_ratio` : score minimum (ratio du max theorique) pour declarer un framework
- `ambiguity_margin` : marge en dessous de laquelle un second framework est considere concurrent (declenchement MIXED)

Valeurs actuelles calibrees sur bootstrap_75 :
- SCI : bien detecte grace aux signaux forts (Save the Children, SCI, IAPSO)
- DGMP : detecte sur base des references au code des marches publics malien
- World Bank / BAD : detecte sur base des references institutionnelles

## Scores framework sur le corpus

Les signaux framework_signals.yaml ont ete valides contre le corpus :
- Signaux SCI (strong) : `save the children`, `sci`, `iapso`, `field procurement handbook`
- Signaux SCI (medium) : `country office`, `bureau pays`, `child safeguarding`
- Signaux DGMP (strong) : `dgmp`, `code des marches publics`, `decret`
- Signaux World Bank (strong) : `world bank`, `banque mondiale`, `procurement framework`
- Signaux BAD (strong) : `banque africaine de developpement`, `bad`

Aucun ajustement de poids n'a ete necessaire pour atteindre le seuil 0.85.
