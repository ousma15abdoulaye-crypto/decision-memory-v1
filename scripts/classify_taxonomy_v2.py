# scripts/classify_taxonomy_v2.py
"""
M7.4 Phase A — Classification L1/L2/L3 par LLM Mistral.

Failles corrigées :
  F-JSON : parser défensif accepte objet ET liste
  F-IDS  : prompt injecte IDs L1+L2+L3 exacts depuis DB
  F-CONN : connexion DB ouverte/fermée par batch · pas globale
  F-LOGP : logprobs supprimé (non supporté Mistral)
  F-KEY  : DMSAPIMISTRAL | DMS_MISTRAL | MISTRAL_API_KEY

DA-TAXO-DB : taxonomie chargée depuis PostgreSQL au démarrage
RÈGLE-25   : LLM propose · AO valide · jamais l'inverse
RÈGLE-42   : --dry-run = zéro appel API · zéro écriture
RÈGLE-V1   : taxo_proposals_v2 uniquement · jamais UPDATE dict_items direct
RÈGLE-J3   : batch tronqué → items manquants → flagged résiduel
RÈGLE-R1   : retry exponentiel 3× · jitter ±0.5s
RÈGLE-R2   : 400/401/403 → STOP immédiat

Usage :
    $env:DATABASE_URL  = "postgresql://..."
    $env:DMSAPIMISTRAL = "<clé>"

    python scripts/classify_taxonomy_v2.py --estimate
    python scripts/classify_taxonomy_v2.py --dry-run --sample 10
    python scripts/classify_taxonomy_v2.py --mode sync --sample 50
    python scripts/classify_taxonomy_v2.py --mode sync
    python scripts/classify_taxonomy_v2.py --mode batch
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)

# ─── Config ──────────────────────────────────────────────────────────────────

MODEL = "mistral-small-latest"
TAXO_VERSION = "2.0.0"
CONF_SEUIL = 0.75
MAX_RETRY = 3
BATCH_SYNC = 10
BATCH_ASYNC = 500
MAX_COST_USD = 10.0
COST_IN = float(os.environ.get("M7_COST_IN", "0.2"))
COST_OUT = float(os.environ.get("M7_COST_OUT", "0.6"))
TOKENS_IN = 600 * BATCH_SYNC
TOKENS_OUT = 150 * BATCH_SYNC
RESIDUEL_L3 = "DIVERS_NON_CLASSE"


# ─── URL + clé ───────────────────────────────────────────────────────────────


def get_db_url() -> str:
    """RÈGLE-39 · normalisation psycopg3."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("❌ DATABASE_URL manquante")
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def get_mistral_key() -> str:
    """F-KEY : 3 noms de variable acceptés."""
    key = (
        os.environ.get("DMSAPIMISTRAL")
        or os.environ.get("DMS_MISTRAL")
        or os.environ.get("MISTRAL_API_KEY")
    )
    if not key:
        sys.exit(
            "❌ Clé Mistral manquante. "
            "Définir DMSAPIMISTRAL, DMS_MISTRAL ou MISTRAL_API_KEY"
        )
    return key


# ─── Taxonomie depuis DB · DA-TAXO-DB ────────────────────────────────────────


class Taxonomy:
    """
    Chargée une fois depuis PostgreSQL au démarrage.
    Le code ne contient aucune liste L1/L2/L3 hardcodée.
    Connexion fermée immédiatement après chargement.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        l1 = conn.execute(
            "SELECT domain_id, label_fr FROM couche_b.taxo_l1_domains"
        ).fetchall()
        l2 = conn.execute(
            "SELECT family_l2_id, domain_id, label_fr " "FROM couche_b.taxo_l2_families"
        ).fetchall()
        l3 = conn.execute(
            "SELECT subfamily_id, family_l2_id, label_fr "
            "FROM couche_b.taxo_l3_subfamilies"
        ).fetchall()

        if not l1 or not l2 or not l3:
            sys.exit(
                "❌ STOP-DB : taxonomie vide. "
                "Lancer scripts/seed_taxonomy_v2.py avant Phase A."
            )

        self.valid_l1: frozenset[str] = frozenset(r["domain_id"] for r in l1)
        self.valid_l2: frozenset[str] = frozenset(r["family_l2_id"] for r in l2)
        self.valid_l3: frozenset[str] = frozenset(r["subfamily_id"] for r in l3)
        self.l2_to_l1: dict[str, str] = {r["family_l2_id"]: r["domain_id"] for r in l2}
        self.l3_to_l2: dict[str, str] = {
            r["subfamily_id"]: r["family_l2_id"] for r in l3
        }

        # Labels pour le prompt
        self.l1_labels: dict[str, str] = {r["domain_id"]: r["label_fr"] for r in l1}
        self.l2_labels: dict[str, str] = {r["family_l2_id"]: r["label_fr"] for r in l2}
        self.l3_labels: dict[str, str] = {r["subfamily_id"]: r["label_fr"] for r in l3}

    def validate(
        self,
        domain_id: str,
        family_l2_id: str,
        subfamily_id: str,
    ) -> tuple[bool, str]:
        if domain_id not in self.valid_l1:
            return False, f"domain_id '{domain_id}' invalide"
        if family_l2_id not in self.valid_l2:
            return False, f"family_l2_id '{family_l2_id}' invalide"
        if subfamily_id not in self.valid_l3:
            return False, f"subfamily_id '{subfamily_id}' invalide"
        expected_l1 = self.l2_to_l1.get(family_l2_id)
        if expected_l1 and expected_l1 != domain_id:
            return False, (
                f"FK L1→L2 incohérente : "
                f"'{family_l2_id}' appartient à '{expected_l1}' "
                f"pas '{domain_id}'"
            )
        return True, ""

    def residuel(self) -> tuple[str, str, str]:
        return "SERVICESGEN", "DIVERS", RESIDUEL_L3


# ─── Pydantic V2 ─────────────────────────────────────────────────────────────

# Instance globale · chargée après connexion DB initiale
_TAXO: Optional[Taxonomy] = None


class TaxoProposal(BaseModel):
    domain_id: str
    family_l2_id: str
    subfamily_id: str
    confidence: float
    raison: str
    confidence_source: str = "llm_self_report"

    @field_validator("confidence")
    @classmethod
    def valid_conf(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence {v} hors [0.0, 1.0]")
        return round(v, 4)

    @model_validator(mode="after")
    def check_fk(self) -> "TaxoProposal":
        """FK L1→L2 validée depuis taxonomie DB."""
        if _TAXO is None:
            return self
        ok, reason = _TAXO.validate(
            self.domain_id, self.family_l2_id, self.subfamily_id
        )
        if not ok:
            raise ValueError(reason)
        return self


# ─── Prompt · F-IDS : IDs L1+L2+L3 exacts depuis DB ─────────────────────────

PROMPT_SYSTEM = (
    "Tu es expert en procurement Afrique de l'Ouest francophone. "
    "ONG · État · mines · construction — Mali. "
    "Tu classifies des articles dans une taxonomie 3 niveaux. "
    "RÉPONDS UNIQUEMENT EN JSON VALIDE. ZÉRO texte hors JSON."
)


def build_prompt(items: list[dict], taxo: Taxonomy) -> str:
    """
    F-IDS : injecter les codes L1 + L2 exacts depuis DB.
    Le LLM ne peut pas inventer ce qu'on lui donne explicitement.
    L3 : exemples représentatifs (prompt resterait sous 4k tokens).
    """
    # L1 → L2 complet
    l1_l2_lines: list[str] = []
    for l1_id in sorted(taxo.valid_l1):
        l2_children = sorted(f2 for f2, p in taxo.l2_to_l1.items() if p == l1_id)
        l2_str = " | ".join(l2_children)
        l1_label = taxo.l1_labels.get(l1_id, "")
        l1_l2_lines.append(f"  {l1_id} ({l1_label}) → {l2_str}")

    l1_l2_text = "\n".join(l1_l2_lines)

    # L3 : tous les codes (le prompt les liste pour éviter toute invention)
    l3_lines = " | ".join(sorted(taxo.valid_l3))

    items_text = "\n".join(
        f'{i+1}. id="{it["item_id"]}" '
        f'label="{it["label_fr"]}" '
        f'slug="{it.get("canonical_slug", "")}"'
        for i, it in enumerate(items)
    )

    return f"""ARTICLES À CLASSIFIER ({len(items)}) :
{items_text}

TAXONOMIE OBLIGATOIRE — CODES EXACTS UNIQUEMENT :

NIVEAU L1 → L2 :
{l1_l2_text}

NIVEAU L3 (codes valides) :
{l3_lines}

RÈGLES ABSOLUES :
· domain_id    = CODE L1 EXACT (ex : CARBLUB · pas "Carburants")
· family_l2_id = CODE L2 EXACT (ex : CARBURANTS · pas "carburant")
· subfamily_id = CODE L3 EXACT (ex : gasoil · pas "Gasoïl")
· Si incertain → SERVICESGEN / DIVERS / DIVERS_NON_CLASSE
· confidence   = certitude réelle 0.0→1.0
· raison       = 1 phrase maximum

FORMAT JSON — STRUCTURE EXACTE OBLIGATOIRE :
{{
  "classifications": [
    {{
      "domain_id":    "CODE_L1",
      "family_l2_id": "CODE_L2",
      "subfamily_id": "CODE_L3",
      "confidence":   0.85,
      "raison":       "1 phrase"
    }}
  ]
}}

EXACTEMENT {len(items)} objets dans "classifications" · même ordre.
ZÉRO code inventé. ZÉRO texte hors JSON."""


# ─── Parser défensif · F-JSON ─────────────────────────────────────────────────


def parse_llm_response(
    raw: str,
) -> tuple[list[dict], Optional[str]]:
    """
    F-JSON : accepte objet {"classifications": [...]} ET liste directe [...].
    Retourne (items_valides, error_msg_ou_None).
    Jamais de crash · toujours un fallback.
    """
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        return [], f"JSONDecodeError: {e}"

    # Cas A : format attendu
    if isinstance(parsed, dict) and "classifications" in parsed:
        candidates = parsed["classifications"]

    # Cas B : liste directe (LLM a omis l'enveloppe)
    elif isinstance(parsed, list):
        candidates = parsed

    # Cas C : objet avec une autre clé contenant une liste
    elif isinstance(parsed, dict):
        found: list = []
        for val in parsed.values():
            if isinstance(val, list) and len(val) > 0:
                found = val
                break
        if not found:
            return [], f"Objet JSON sans liste · clés trouvées : {list(parsed.keys())}"
        candidates = found

    else:
        return [], f"Format inattendu : {type(parsed).__name__}"

    if not isinstance(candidates, list):
        return [], f"candidates n'est pas une liste : {type(candidates).__name__}"

    # Filtrer les dicts valides minimalement
    valid = [c for c in candidates if isinstance(c, dict) and "domain_id" in c]

    if not valid:
        return [], "Aucun objet avec domain_id trouvé dans la réponse"

    return valid, None


# ─── API Mistral · F-LOGP supprimé ───────────────────────────────────────────


def mistral_post(
    payload: dict,
    report: "TaxoReport",
    key: str,
) -> Optional[dict]:
    """
    RÈGLE-J1 : json_object forcé.
    F-LOGP   : logprobs supprimé (non supporté Mistral).
    RÈGLE-R1 : retry exponentiel 3× + jitter.
    RÈGLE-R2 : 400/401/403 → STOP immédiat.
    """
    import urllib.error
    import urllib.request

    data = json.dumps(
        {
            **payload,
            "response_format": {"type": "json_object"},
            # logprobs intentionnellement absent · F-LOGP
        }
    ).encode()

    for attempt in range(1, MAX_RETRY + 1):
        try:
            req = urllib.request.Request(
                "https://api.mistral.ai/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                usage = result.get("usage", {})
                report.cost_usd += (
                    usage.get("prompt_tokens", TOKENS_IN) * COST_IN / 1_000_000
                    + usage.get("completion_tokens", TOKENS_OUT) * COST_OUT / 1_000_000
                )
                return result

        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):
                logger.error(f"HTTP {e.code} · STOP-R2 · non retryable")
                raise
            delay = 2**attempt + random.uniform(-0.5, 0.5)
            logger.warning(
                f"HTTP {e.code} · attempt {attempt}/{MAX_RETRY} "
                f"· retry {delay:.1f}s"
            )
            time.sleep(delay)

        except Exception as e:
            delay = 2**attempt
            logger.warning(f"Réseau attempt {attempt} : {e} · retry {delay}s")
            time.sleep(delay)

    logger.error("MAX_RETRY atteint · batch abandonné")
    return None


# ─── Persistance ─────────────────────────────────────────────────────────────


def build_prompt_hash(item_ids: list[str], prompt: str) -> str:
    return hashlib.sha256(
        (MODEL + TAXO_VERSION + "|".join(sorted(item_ids)) + prompt).encode()
    ).hexdigest()[:32]


def already_done(
    conn: psycopg.Connection,
    item_id: str,
    ph: str,
) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM couche_b.taxo_proposals_v2 "
            "WHERE item_id=%s AND taxo_version=%s "
            "AND model=%s AND prompt_hash=%s",
            (item_id, TAXO_VERSION, MODEL, ph),
        ).fetchone()
        is not None
    )


def insert_proposal(
    conn: psycopg.Connection,
    item_id: str,
    prop: TaxoProposal,
    ph: str,
    status: str,
    batch_job_id: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO couche_b.taxo_proposals_v2 (
            item_id, domain_id, family_l2_id, subfamily_id,
            confidence, reason, model, prompt_hash, taxo_version,
            status, confidence_source, batch_job_id
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (item_id, taxo_version, model, prompt_hash)
        DO NOTHING
    """,
        (
            item_id,
            prop.domain_id,
            prop.family_l2_id,
            prop.subfamily_id,
            prop.confidence,
            prop.raison,
            MODEL,
            ph,
            TAXO_VERSION,
            status,
            prop.confidence_source,
            batch_job_id,
        ),
    )


# ─── Report ──────────────────────────────────────────────────────────────────


@dataclass
class TaxoReport:
    total: int = 0
    batches: int = 0
    inserted: int = 0
    skipped: int = 0
    flagged: int = 0
    residuel: int = 0
    truncated: int = 0
    errors: int = 0
    cost_usd: float = 0.0
    samples: list = field(default_factory=list)

    def _proc(self) -> int:
        return self.inserted + self.flagged

    def flag_pct(self) -> float:
        p = self._proc()
        return round(self.flagged / p * 100, 1) if p else 0.0

    def resid_pct(self) -> float:
        p = self._proc()
        return round(self.residuel / p * 100, 1) if p else 0.0

    def cost_per_item(self) -> float:
        return TOKENS_IN * COST_IN / 1_000_000 + TOKENS_OUT * COST_OUT / 1_000_000

    def summary(self) -> str:
        lines = [
            "=" * 65,
            "RAPPORT M7.4 PHASE A",
            "=" * 65,
            f"  Items chargés      : {self.total}",
            f"  Batches LLM        : {self.batches}",
            f"  Insérés proposals  : {self.inserted}",
            f"  Skippés            : {self.skipped}",
            f"  Flaggés            : {self.flagged} ({self.flag_pct()}%)",
            f"  Résiduel DIVERS    : {self.residuel} ({self.resid_pct()}%)",
            f"  Batches tronqués   : {self.truncated}",
            f"  Erreurs            : {self.errors}",
            f"  Coût réel          : ${self.cost_usd:.4f} USD",
        ]
        if self.flag_pct() > 35:
            lines.append(f"  [!] STOP-V3 : flagged {self.flag_pct()}% > 35%")
        if self.resid_pct() > 25:
            lines.append(f"  [!] STOP-V4 : residuel {self.resid_pct()}% > 25%")
        if self.samples:
            lines.append("  ÉCHANTILLON :")
            for s in self.samples[:10]:
                lines.append(
                    f"    [{s['status']:<8}] "
                    f"{s['label'][:22]:<22} -> "
                    f"{s['l1']:<14} conf={s['conf']:.2f}"
                )
        lines.append("=" * 65)
        return "\n".join(lines)


# ─── Core batch · F-CONN : connexion par batch ───────────────────────────────


def _make_fallback(taxo: Taxonomy, reason: str) -> TaxoProposal:
    rl1, rl2, rl3 = taxo.residuel()
    return TaxoProposal(
        domain_id=rl1,
        family_l2_id=rl2,
        subfamily_id=rl3,
        confidence=0.0,
        raison=reason[:80],
    )


def _insert_flagged_batch(
    conn: psycopg.Connection,
    batch: list[dict],
    taxo: Taxonomy,
    ph: str,
    reason: str,
    report: TaxoReport,
) -> None:
    """Insère tout un batch comme flagged résiduel."""
    for item in batch:
        try:
            with conn.transaction():
                insert_proposal(
                    conn,
                    item["item_id"],
                    _make_fallback(taxo, reason),
                    ph,
                    "flagged",
                )
            report.flagged += 1
        except Exception as e:
            logger.warning(f"Insert fallback {item['item_id']}: {e}")
            report.errors += 1


def process_single_batch(
    batch: list[dict],
    taxo: Taxonomy,
    report: TaxoReport,
    key: str,
    db_url: str,
) -> None:
    """
    F-CONN : connexion DB ouverte/fermée par batch.
    Appel LLM hors connexion → zéro idle timeout Railway.
    F-JSON : parser défensif sur la réponse.
    F3     : batch tronqué → items manquants → flagged.
    Pydantic + FK L1→L2 sur chaque proposal.
    SAVEPOINT par item (psycopg3 nested transaction).
    """
    prompt = build_prompt(batch, taxo)
    ph = build_prompt_hash([it["item_id"] for it in batch], prompt)
    report.batches += 1

    # ── Appel LLM · connexion DB fermée ──────────────────────────────
    result = mistral_post(
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": PROMPT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
        },
        report,
        key,
    )

    if result is None:
        # Retry épuisé · marquer tout le batch erreur sans DB
        report.errors += len(batch)
        logger.warning(
            f"Batch abandonné après MAX_RETRY · {len(batch)} items non insérés"
        )
        return

    raw = result["choices"][0]["message"]["content"]
    items_parsed, error = parse_llm_response(raw)

    # ── Écriture DB · connexion ouverte ici uniquement ───────────────
    with psycopg.connect(db_url, row_factory=dict_row) as conn:

        # Parse échoué total → tout le batch flagged
        if error or not items_parsed:
            logger.warning(f"Parse échoué : {error}")
            _insert_flagged_batch(
                conn,
                batch,
                taxo,
                ph,
                f"parse_error:{(error or 'empty')[:40]}",
                report,
            )
            conn.commit()
            return

        # F3 · batch tronqué → items manquants → flagged
        if len(items_parsed) < len(batch):
            missing = batch[len(items_parsed) :]
            logger.warning(
                f"Batch tronqué : attendu {len(batch)} "
                f"· reçu {len(items_parsed)} "
                f"· {len(missing)} → flagged"
            )
            report.truncated += 1
            _insert_flagged_batch(
                conn,
                missing,
                taxo,
                ph,
                "batch_truncation",
                report,
            )

        # Traiter les items reçus
        for item, raw_prop in zip(batch, items_parsed):

            if already_done(conn, item["item_id"], ph):
                report.skipped += 1
                continue

            # Validation Pydantic + FK L1→L2
            try:
                prop = TaxoProposal(**raw_prop)
            except Exception as e:
                logger.warning(f"Pydantic {item['item_id']}: {e} · flagged")
                prop = _make_fallback(taxo, f"pydantic:{str(e)[:40]}")
                status = "flagged"
                report.flagged += 1
            else:
                is_residuel = prop.subfamily_id == RESIDUEL_L3
                if prop.confidence >= CONF_SEUIL and not is_residuel:
                    status = "pending"
                    report.inserted += 1
                else:
                    status = "flagged"
                    report.flagged += 1
                    if is_residuel:
                        report.residuel += 1

            try:
                with conn.transaction():
                    insert_proposal(conn, item["item_id"], prop, ph, status)
            except Exception as e:
                logger.warning(f"Insert {item['item_id']}: {e}")
                report.errors += 1

            if len(report.samples) < 20:
                report.samples.append(
                    {
                        "label": item["label_fr"],
                        "l1": prop.domain_id,
                        "conf": prop.confidence,
                        "status": status,
                    }
                )

        conn.commit()
        logger.info(
            f"Batch OK · +{report.inserted} pending "
            f"· {report.flagged} flagged "
            f"· coût ${report.cost_usd:.4f}"
        )


# ─── Load items ──────────────────────────────────────────────────────────────


def load_items(
    conn: psycopg.Connection,
    limit: Optional[int] = None,
) -> list[dict]:
    sql = """
        SELECT item_id, label_fr, canonical_slug
        FROM couche_b.procurement_dict_items
        WHERE active       = TRUE
          AND domain_id    IS NULL
          AND label_fr     IS NOT NULL
          AND LENGTH(TRIM(label_fr)) > 5
          AND COALESCE(canonical_slug, '') !~ '^[0-9]+$'
        ORDER BY item_id
    """
    if limit:
        sql += f" LIMIT {limit}"
    return [dict(r) for r in conn.execute(sql).fetchall()]


# ─── Mode SYNC ───────────────────────────────────────────────────────────────


def run_sync(
    items: list[dict],
    taxo: Taxonomy,
    report: TaxoReport,
    dry_run: bool,
    key: str,
    db_url: str,
) -> None:
    """F-CONN : connexion par batch · pas globale."""
    for i in range(0, len(items), BATCH_SYNC):
        batch = items[i : i + BATCH_SYNC]

        if dry_run:
            report.batches += 1
            report.cost_usd += report.cost_per_item() * len(batch)
            logger.info(
                f"DRY-RUN batch {i//BATCH_SYNC+1} "
                f"({len(batch)} items) · zéro appel API"
            )
            continue

        process_single_batch(batch, taxo, report, key, db_url)

        if i > 0 and i % 100 == 0:
            logger.info(
                f"Progression {i}/{len(items)} " f"· coût ${report.cost_usd:.4f}"
            )


# ─── Mode BATCH API ──────────────────────────────────────────────────────────


def run_batch_api(
    items: list[dict],
    conn: psycopg.Connection,
    report: TaxoReport,
    taxo: Taxonomy,
    key: str,
) -> None:
    """
    Mistral Batch API · 50% coût.
    DA-LOOKUP : items_by_id dict O(1).
    Poll adaptatif 10s → 120s.
    """
    import urllib.error
    import urllib.request

    items_by_id: dict[str, dict] = {it["item_id"]: it for it in items}
    ph_map: dict[str, str] = {}

    def api_call(
        method: str,
        path: str,
        data: Optional[bytes] = None,
        content_type: str = "application/json",
    ) -> dict:
        req = urllib.request.Request(
            f"https://api.mistral.ai{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": content_type,
            },
            method=method,
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    # Construire JSONL
    lines = []
    for item in items:
        prompt = build_prompt([item], taxo)
        ph = build_prompt_hash([item["item_id"]], prompt)
        ph_map[item["item_id"]] = ph
        lines.append(
            json.dumps(
                {
                    "custom_id": item["item_id"],
                    "body": {
                        "model": MODEL,
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1,
                        "max_tokens": 400,
                        "messages": [
                            {"role": "system", "content": PROMPT_SYSTEM},
                            {"role": "user", "content": prompt},
                        ],
                    },
                }
            )
        )

    jsonl_bytes = "\n".join(lines).encode()
    report.batches = 1

    # Upload
    boundary = uuid.uuid4().hex
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; '
            f'filename="m74_batch.jsonl"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + jsonl_bytes
        + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="purpose"\r\n\r\n'
            f"batch\r\n--{boundary}--\r\n"
        ).encode()
    )

    upload = api_call(
        "POST",
        "/v1/files",
        body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    file_id = upload["id"]
    logger.info(f"Fichier uploadé : {file_id}")

    job = api_call(
        "POST",
        "/v1/batch/jobs",
        json.dumps(
            {
                "input_files": [file_id],
                "model": MODEL,
                "endpoint": "/v1/chat/completions",
                "metadata": {"mandat": "M7.4", "taxo_version": TAXO_VERSION},
            }
        ).encode(),
    )
    job_id = job["id"]
    logger.info(f"Job batch : {job_id}")

    # Poll adaptatif
    poll_int = 10
    max_poll = 120
    max_wait = 7200
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_int)
        elapsed += poll_int
        status_r = api_call("GET", f"/v1/batch/jobs/{job_id}")
        status = status_r.get("status")
        logger.info(f"Job {job_id} · {status} · {elapsed}s")
        if status in ("SUCCESS", "FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"):
            break
        poll_int = min(poll_int * 1.5, max_poll)
    else:
        sys.exit(f"Batch job timeout après {max_wait}s")

    if status != "SUCCESS":
        sys.exit(f"Batch job terminé avec status={status}")

    # Download résultats
    req = urllib.request.Request(
        f"https://api.mistral.ai/v1/files/{status_r['output_file']}/content",
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result_lines = resp.read().decode().strip().split("\n")

    for line in result_lines:
        r = json.loads(line)
        item_id = r["custom_id"]
        item = items_by_id.get(item_id)
        if item is None:
            continue
        ph = ph_map.get(item_id, "batch_unknown")
        body_r = r.get("response", {}).get("body", {})
        raw = body_r.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = body_r.get("usage", {})
        report.cost_usd += (
            usage.get("prompt_tokens", 600) * COST_IN * 0.5 / 1_000_000
            + usage.get("completion_tokens", 150) * COST_OUT * 0.5 / 1_000_000
        )
        items_parsed, error = parse_llm_response(raw)
        if error or not items_parsed:
            _insert_flagged_batch(
                conn,
                [item],
                taxo,
                ph,
                f"batch_parse_error:{(error or 'empty')[:30]}",
                report,
            )
        else:
            try:
                prop = TaxoProposal(**items_parsed[0])
            except Exception as e:
                prop = _make_fallback(taxo, f"pydantic:{str(e)[:40]}")
                with conn.transaction():
                    insert_proposal(conn, item_id, prop, ph, "flagged")
                report.flagged += 1
            else:
                is_residuel = prop.subfamily_id == RESIDUEL_L3
                status_p = (
                    "pending"
                    if prop.confidence >= CONF_SEUIL and not is_residuel
                    else "flagged"
                )
                try:
                    with conn.transaction():
                        insert_proposal(conn, item_id, prop, ph, status_p)
                    if status_p == "pending":
                        report.inserted += 1
                    else:
                        report.flagged += 1
                except Exception as e:
                    logger.warning(f"Insert batch {item_id}: {e}")
                    report.errors += 1

    conn.commit()


# ─── Entry point ─────────────────────────────────────────────────────────────


def main() -> None:
    global _TAXO

    parser = argparse.ArgumentParser(
        description="M7.4 Phase A · Classification taxonomie"
    )
    parser.add_argument("--mode", choices=["sync", "batch"], default="sync")
    parser.add_argument("--sample", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--estimate", action="store_true")
    args = parser.parse_args()

    db_url = get_db_url()
    key = "" if (args.dry_run or args.estimate) else get_mistral_key()
    report = TaxoReport()

    # Chargement initial : connexion courte · fermée avant appels LLM
    # F-CONN : zéro connexion idle pendant les appels API
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        taxo = Taxonomy(conn)
        _TAXO = taxo  # injecté dans TaxoProposal.check_fk
        items = load_items(conn, limit=args.sample)
        report.total = len(items)
    # connexion fermée ici

    if args.estimate:
        n_calls = math.ceil(len(items) / BATCH_SYNC)
        cost_sync = n_calls * (
            TOKENS_IN * COST_IN / 1_000_000 + TOKENS_OUT * COST_OUT / 1_000_000
        )
        cost_batch = cost_sync * 0.5
        print(f"Items          : {len(items)}")
        print(f"Coût SYNC      : ${cost_sync:.4f}")
        print(f"Coût BATCH     : ${cost_batch:.4f} (recommandé si > $2)")
        if cost_sync > MAX_COST_USD:
            print(f"[!] STOP-V2 : cout SYNC > ${MAX_COST_USD} -> --mode batch")
        return

    if args.mode == "batch" and not args.dry_run:
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            run_batch_api(items, conn, report, taxo, key)
    else:
        run_sync(items, taxo, report, args.dry_run, key, db_url)

    print(report.summary())

    if not args.dry_run:
        if report.flag_pct() > 35:
            sys.exit(1)
        if report.resid_pct() > 25:
            sys.exit(1)


if __name__ == "__main__":
    main()
