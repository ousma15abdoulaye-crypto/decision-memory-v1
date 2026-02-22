"""M-PARSING-MERCURIALE -- Parser deterministe (Couche B, memoire only).

PARSE-001 : raw_line toujours conservee.
PARSE-002 : erreurs dans parse_errors, jamais silencieux.
PARSE-003 : nombres avec espaces + virgules (ex: 73 833, 1 250,50).
PARSE-004 : 3 prix consecutifs -> map sur min/avg/max.
PARSE-005 : parse_batch() appelle normalize_batch() une seule fois.
PARSE-006 : multi-ligne : accumulation des segments designation avant prix.

Aucun import Couche A. Aucun fuzzy. Deterministe uniquement.
ADR-0002 strict.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from src.couche_b.mercuriale.schemas import MercurialeParsedLine, ParseStatus
from src.couche_b.normalisation.engine import normalize_batch

# ---------------------------------------------------------------------------
# Regex utilitaires
# ---------------------------------------------------------------------------

# Montant : entiers ou decimaux avec separateur espace/apostrophe + virgule decimale
# Ex: "73 833"  "1 250,50"  "84000"  "1250.50"
_RE_AMOUNT = re.compile(r"\b(\d{1,3}(?:[\s\u00a0']\d{3})*(?:[.,]\d{1,4})?)\b")

# Sequence de 3 montants consecutifs (avec separateurs optionnels entre eux)
_RE_THREE_PRICES = re.compile(
    r"(\d{1,3}(?:[\s\u00a0']\d{3})*(?:[.,]\d{1,4})?)"
    r"[\s\t]+"
    r"(\d{1,3}(?:[\s\u00a0']\d{3})*(?:[.,]\d{1,4})?)"
    r"[\s\t]+"
    r"(\d{1,3}(?:[\s\u00a0']\d{3})*(?:[.,]\d{1,4})?)"
)

# Ligne quasi-vide ou purement decorative
_RE_DECORATIVE = re.compile(r"^[\s|_\-=#+*\.]{0,5}$")


# ---------------------------------------------------------------------------
# Helpers numeriques
# ---------------------------------------------------------------------------


def _parse_amount(raw: str) -> float:
    """Convertit une chaine montant en float (PARSE-003).

    "73 833"    -> 73833.0
    "1 250,50"  -> 1250.5
    "84 000"    -> 84000.0
    """
    cleaned = re.sub(r"[\s\u00a0']", "", raw)  # supprimer separateurs milliers
    cleaned = cleaned.replace(",", ".")  # virgule decimale -> point
    return float(cleaned)


# ---------------------------------------------------------------------------
# Draft intermediaire (avant normalisation)
# ---------------------------------------------------------------------------


@dataclass
class _ParsedDraft:
    """Resultat intermediaire avant appel normalize_batch."""

    raw_line: str
    designation_raw: str | None = None
    unite_raw: str | None = None
    price_min: float | None = None
    price_avg: float | None = None
    price_max: float | None = None
    currency: str = "XOF"
    status: ParseStatus = ParseStatus.UNPARSEABLE
    parse_errors: list[str] = field(default_factory=list)


def parse_line(raw_line: str) -> _ParsedDraft:
    """Parse une seule ligne de maniere deterministe.

    Strategie :
    1. Si decorative / vide -> unparseable
    2. Cherche 3 prix consecutifs (PARSE-004)
    3. Si trouves : le texte avant = designation candidate, apres = unite candidate
    4. Si pas de prix : designation seule -> partial
    """
    draft = _ParsedDraft(raw_line=raw_line)

    # Ligne purement decorative
    if _RE_DECORATIVE.match(raw_line.strip()):
        draft.parse_errors.append("decorative or empty line")
        draft.status = ParseStatus.UNPARSEABLE
        return draft

    stripped = raw_line.strip()

    # Recherche de 3 prix (PARSE-004)
    m = _RE_THREE_PRICES.search(stripped)
    if m:
        try:
            draft.price_min = _parse_amount(m.group(1))
            draft.price_avg = _parse_amount(m.group(2))
            draft.price_max = _parse_amount(m.group(3))
        except ValueError as exc:
            draft.parse_errors.append(f"price parse error: {exc}")
            draft.status = ParseStatus.UNPARSEABLE
            return draft

        # Texte avant les prix -> designation + unite
        before = stripped[: m.start()].strip()
        after = stripped[m.end() :].strip()

        # Heuristique : dernier "mot" avant les prix peut etre l'unite
        # si le texte avant comporte plusieurs mots
        parts = before.rsplit(None, 1)
        if len(parts) == 2:
            candidate_unit = parts[1].strip()
            # Unite : courte (<=20 chars) et sans chiffre au debut
            if len(candidate_unit) <= 20 and not candidate_unit[0].isdigit():
                draft.designation_raw = parts[0].strip() or None
                draft.unite_raw = candidate_unit
            else:
                draft.designation_raw = before or None
        elif len(parts) == 1:
            draft.designation_raw = parts[0].strip() or None

        # Fallback : si unite dans le texte apres les prix
        if draft.unite_raw is None and after:
            draft.unite_raw = after[:50] or None

        if draft.unite_raw is None:
            draft.parse_errors.append("unit missing")
            draft.status = ParseStatus.PARTIAL
        else:
            draft.status = ParseStatus.OK

        return draft

    # Pas de 3 prix : cherche au moins 1 montant
    amounts = _RE_AMOUNT.findall(stripped)
    if amounts:
        draft.parse_errors.append(
            f"found {len(amounts)} price(s) but expected 3 (min/avg/max)"
        )
        # Recuperer ce qu'on peut
        if len(amounts) >= 1:
            try:
                draft.price_min = _parse_amount(amounts[0])
            except ValueError:
                pass
        draft.designation_raw = stripped or None
        draft.status = ParseStatus.PARTIAL
        return draft

    # Aucun montant : designation seule (candidat multi-ligne PARSE-006)
    if stripped:
        draft.designation_raw = stripped
        draft.parse_errors.append("no prices found")
        draft.status = ParseStatus.PARTIAL
    else:
        draft.parse_errors.append("empty line")
        draft.status = ParseStatus.UNPARSEABLE

    return draft


# ---------------------------------------------------------------------------
# Batch avec gestion multi-ligne (PARSE-006)
# ---------------------------------------------------------------------------


def parse_batch(
    raw_lines: Sequence[str],
    conn,
    source: str | None = None,  # noqa: ARG001
) -> list[MercurialeParsedLine]:
    """Parse un batch de lignes mercuriale.

    PARSE-001 : raw_line = entree brute originale, jamais strippee.
    PARSE-002 : lignes vides -> UNPARSEABLE("EMPTY_LINE"), jamais silencieuses.
    PARSE-005 : normalize_batch() appele une seule fois.
    PARSE-006 : segments designation accumules avant la ligne prix.

    Contrat ordre 1:1 :
      - Chaque ligne vide produit exactement 1 resultat UNPARSEABLE a sa position.
      - Chaque groupe multi-ligne produit exactement 1 resultat (la ligne prix).
      - raw_line = ligne originale si groupe=1 OU concat " | " si groupe>1 (evidence trail).

    Args:
        raw_lines : lignes brutes (peut inclure des segments multi-lignes et vides).
        conn      : connexion psycopg injectee par l'appelant.
        source    : tag source optionnel (non utilise dans le parsing pur).
    """
    if not raw_lines:
        return []

    # --- Phase 1 : construction des groupes logiques (ordre preserve) ---
    # Chaque groupe est soit ("empty", raw) soit ("data", [raws], merged_text).
    # Les lignes vides ne polluent JAMAIS le pipeline multi-ligne (FIX B2).
    groups: list[tuple] = []
    pending_raws: list[str] = []
    pending_stripped: list[str] = []

    for raw in raw_lines:
        stripped = raw.strip()

        if stripped == "":
            # Ligne vide : flush pending, puis groupe vide independant (FIX B2)
            if pending_raws:
                groups.append(("data", pending_raws[:], " ".join(pending_stripped)))
                pending_raws = []
                pending_stripped = []
            groups.append(("empty", raw))

        elif _RE_THREE_PRICES.search(stripped):
            # Ligne avec 3 prix : finalise le groupe en attente
            if pending_raws:
                merged = " ".join(pending_stripped) + " " + stripped
                groups.append(("data", pending_raws + [raw], merged))
                pending_raws = []
                pending_stripped = []
            else:
                groups.append(("data", [raw], stripped))

        elif _RE_DECORATIVE.match(stripped):
            # Decorative non vide (ex: "|||") : flush pending, groupe seul
            if pending_raws:
                groups.append(("data", pending_raws[:], " ".join(pending_stripped)))
                pending_raws = []
                pending_stripped = []
            groups.append(("data", [raw], stripped))

        else:
            # Segment texte sans prix : accumulation (PARSE-006)
            pending_raws.append(raw)
            pending_stripped.append(stripped)

    # Segments residuels non suivis d'une ligne prix
    if pending_raws:
        groups.append(("data", pending_raws[:], " ".join(pending_stripped)))

    # --- Phase 2 : parse individuel des groupes "data" ---
    group_drafts: list[_ParsedDraft | None] = []
    for g in groups:
        if g[0] == "data":
            group_drafts.append(parse_line(g[2]))  # g[2] = merged_text
        else:
            group_drafts.append(None)

    # --- Phase 3 : normalize_batch unique (PARSE-005) ---
    designations = [
        d.designation_raw
        for d in group_drafts
        if d is not None and d.designation_raw and d.status != ParseStatus.UNPARSEABLE
    ]
    norm_map: dict[str, object] = {}
    if designations:
        norm_results = normalize_batch(designations, conn)
        norm_map = {r.input_raw: r for r in norm_results}

    # --- Phase 4 : assembler MercurialeParsedLine (ordre = ordre des groupes) ---
    results: list[MercurialeParsedLine] = []
    for g, draft in zip(groups, group_drafts):
        if g[0] == "empty":
            # Ligne vide : UNPARSEABLE, raw_line = entree originale (FIX B1+B2)
            results.append(
                MercurialeParsedLine(
                    raw_line=g[1],  # original preservee (ex: "")
                    designation_raw=None,
                    unite_raw=None,
                    price_min=None,
                    price_avg=None,
                    price_max=None,
                    currency="XOF",
                    normalisation=None,
                    status=ParseStatus.UNPARSEABLE,
                    parse_errors=["EMPTY_LINE"],
                )
            )
        else:
            # Groupe data : raw_line = original si 1 ligne, concat si multi (FIX B1)
            contributing: list[str] = g[1]
            if len(contributing) == 1:
                raw_line = contributing[0]  # PARSE-001 : original, jamais strip
            else:
                raw_line = " | ".join(contributing)  # append-only evidence trail
            assert draft is not None
            norm = (
                norm_map.get(draft.designation_raw) if draft.designation_raw else None
            )
            results.append(
                MercurialeParsedLine(
                    raw_line=raw_line,
                    designation_raw=draft.designation_raw,
                    unite_raw=draft.unite_raw,
                    price_min=draft.price_min,
                    price_avg=draft.price_avg,
                    price_max=draft.price_max,
                    currency=draft.currency,
                    normalisation=norm,
                    status=draft.status,
                    parse_errors=draft.parse_errors,
                )
            )

    return results
