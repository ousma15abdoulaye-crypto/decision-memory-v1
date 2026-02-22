"""Couche B -- Mercuriale parsing -- facade stable (DMS V3.3.2).

Role : parser des lignes brutes mercuriale (Market Survey / memoire Couche B).
       Retourne des objets structures MercurialeParsedLine avec normalisation.

Interdits :
  - Tout import Couche A (criteria, scoring, pipeline)
  - Ecriture dans couche_b.procurement_dict_*
  - Appel DB direct depuis ce module (injecter conn via parse_batch)
  - Retour None comme resultat global (PARSE-002)
"""

from .parser import parse_batch, parse_line
from .schemas import MercurialeParsedLine, MercurialeParseRequest, ParseStatus

__all__ = [
    "parse_line",
    "parse_batch",
    "MercurialeParsedLine",
    "MercurialeParseRequest",
    "ParseStatus",
]
