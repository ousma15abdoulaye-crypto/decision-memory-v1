"""
M12 LLM Arbitrator — Cerveau semantique du moteur M12.

Appele UNIQUEMENT quand le deterministe doute (confiance < seuil ou not_detected).
Online-first. Jamais de valeur inventee : le LLM choisit parmi les candidats
du deterministe, sa confiance est plafonnee, chaque reponse est un TracedField auditablé.

Architecture :
  - Point d'entree unique pour tous les appels LLM de M12
  - Prompts specialises par tache (pas de mega-prompt generique)
  - temperature=0.0 + response_format JSON — deterministe autant que possible
  - Timeout strict 10s, 1 retry
  - Fallback: retour not_resolved avec confidence=0.0 si API indisponible
  - Extra=forbid sur tous les modeles Pydantic (E-49)

Methodes :
  disambiguate_document_type(text, candidates, deterministic_confidence)
    -> quand L3 type recognizer retourne confidence < seuil ou UNKNOWN

  detect_mandatory_part(text_excerpt, part_name, part_description)
    -> Level 3 LLM fallback dans mandatory_parts_engine (L227 placeholder)

  semantic_link_documents(doc_a_summary, doc_b_summary, text_a_excerpt, text_b_excerpt)
    -> renforce process_linker quand fuzzy < seuil
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from src.procurement.procedure_models import TracedField

logger = logging.getLogger(__name__)

# ── Configuration (constantes fallback) ───────────────────────────────────

_DEFAULT_MODEL = "mistral-large-latest"
_DEFAULT_TIMEOUT = 10
_DEFAULT_MAX_RETRIES = 1
_DEFAULT_TEMPERATURE = 0.0

# Plafonds de confiance par tache (conservateurs — humain valide toujours)
_MAX_CONF_TYPE_DISAMBIGUATION = 0.85
_MAX_CONF_MANDATORY_PART = 0.70
_MAX_CONF_PROCESS_LINK = 0.80

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "llm_arbitration.yaml"


def _load_yaml_config() -> dict:
    """Charge config/llm_arbitration.yaml. Retourne {} si absent ou invalide."""
    if not _CONFIG_PATH.is_file():
        logger.debug(
            "[ARBITRATOR] config/llm_arbitration.yaml absent — constantes par defaut"
        )
        return {}
    try:
        import yaml  # yaml est une dep DMS (mandatory_parts_engine l'utilise deja)

        with _CONFIG_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            logger.warning(
                "[ARBITRATOR] llm_arbitration.yaml mal forme — constantes par defaut"
            )
            return {}
        logger.debug("[ARBITRATOR] llm_arbitration.yaml charge depuis %s", _CONFIG_PATH)
        return data
    except Exception as exc:
        logger.warning(
            "[ARBITRATOR] Impossible de charger llm_arbitration.yaml : %s", exc
        )
        return {}


# ── Singleton ─────────────────────────────────────────────────────────────

_arbitrator_instance: LLMArbitrator | None = None


def get_arbitrator() -> LLMArbitrator:
    """Retourne le singleton LLMArbitrator."""
    global _arbitrator_instance
    if _arbitrator_instance is None:
        _arbitrator_instance = LLMArbitrator()
    return _arbitrator_instance


def reset_arbitrator() -> None:
    """Reinitialise le singleton (utile en tests)."""
    global _arbitrator_instance
    _arbitrator_instance = None


# ── Helpers ───────────────────────────────────────────────────────────────


def _cap(value: float, ceiling: float) -> float:
    return min(float(value), ceiling)


def _safe_json(raw: str) -> dict:
    """Parse JSON avec tolerances (fences markdown, etc.)."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner = [ln for ln in lines if not ln.startswith("```")]
        raw = "\n".join(inner).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "[ARBITRATOR] _safe_json : echec parse JSON (%s) — raw[:120]=%r",
            exc,
            raw[:120],
        )
        return {}


def _parse_bool_strict(value: Any) -> bool | None:
    """Parse un booleen de facon stricte depuis une reponse LLM.

    Accepte : bool natif, ou str 'true'/'false' (insensible a la casse).
    Rejette tout le reste en retournant None.
    Evite que bool('false') -> True (bug classique avec JSON imparfait du LLM).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
    return None


def _not_resolved(task: str, reason: str) -> TracedField:
    """TracedField standard pour un arbitrage non resolu."""
    return TracedField(
        value=None,
        confidence=0.0,
        evidence=[f"llm_arbitration:not_resolved:{reason}", f"task:{task}"],
    )


# ── LLMArbitrator ─────────────────────────────────────────────────────────


class LLMArbitrator:
    """
    Arbitre LLM pour le moteur M12.

    Online-first : ne fait rien (retourne not_resolved) si MISTRAL_API_KEY absent.
    Chaque appel est traçable via TracedField.evidence = ["llm_arbitration:<model>"].
    """

    def __init__(
        self,
        model: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        cfg = _load_yaml_config()
        arb_cfg = cfg.get("arbitration", {})
        thresh_cfg = cfg.get("thresholds", {})

        # Priorite : argument explicite > env var > YAML > constante
        self._model = (
            model
            or os.environ.get("LLM_ARBITRATOR_MODEL")
            or arb_cfg.get("model")
            or _DEFAULT_MODEL
        )
        self._timeout = timeout or int(
            os.environ.get("LLM_ARBITRATOR_TIMEOUT")
            or arb_cfg.get("timeout_seconds")
            or _DEFAULT_TIMEOUT
        )
        self._max_retries = max_retries or int(
            os.environ.get("LLM_ARBITRATOR_MAX_RETRIES")
            or arb_cfg.get("max_retries")
            or _DEFAULT_MAX_RETRIES
        )
        self._enabled = arb_cfg.get("enabled", True)

        # Plafonds par tache — depuis YAML si present, sinon constantes module
        td = thresh_cfg.get("type_disambiguation", {})
        mp = thresh_cfg.get("mandatory_parts_l3", {})
        pl = thresh_cfg.get("process_linking", {})
        self._max_conf_type = float(
            td.get("max_llm_confidence", _MAX_CONF_TYPE_DISAMBIGUATION)
        )
        self._max_conf_parts = float(
            mp.get("max_llm_confidence", _MAX_CONF_MANDATORY_PART)
        )
        self._max_conf_link = float(
            pl.get("max_llm_confidence", _MAX_CONF_PROCESS_LINK)
        )
        self._trigger_type_below = float(td.get("trigger_below_confidence", 0.80))

        logger.debug(
            "[ARBITRATOR] init model=%s timeout=%ds retries=%d enabled=%s",
            self._model,
            self._timeout,
            self._max_retries,
            self._enabled,
        )

    def is_available(self) -> bool:
        """True si arbitrateur actif ET MISTRAL_API_KEY presente.

        Ordre de priorite :
        1. Env var LLM_ARBITRATOR_ENABLED=false -> desactive (killswitch Railway)
        2. YAML arbitration.enabled=false -> desactive
        3. MISTRAL_API_KEY absente -> indisponible
        """
        env_enabled = os.environ.get("LLM_ARBITRATOR_ENABLED", "").strip().lower()
        if env_enabled == "false":
            logger.debug(
                "[ARBITRATOR] desactive par LLM_ARBITRATOR_ENABLED=false (env)"
            )
            return False
        if not self._enabled:
            logger.debug("[ARBITRATOR] desactive par config YAML (enabled=false)")
            return False
        return bool(os.environ.get("MISTRAL_API_KEY", "").strip())

    def _get_client(self):
        """Retourne un client Mistral configure."""
        from src.couche_a.llm_router import get_llm_client

        return get_llm_client()

    def _call(self, messages: list[dict[str, str]]) -> str | None:
        """
        Appel LLM avec timeout + retry.
        Retourne le texte brut de la reponse ou None si echec.
        """
        if not self.is_available():
            logger.debug("[ARBITRATOR] MISTRAL_API_KEY absente — skip")
            return None

        client = self._get_client()
        last_exc = None

        for attempt in range(1, self._max_retries + 2):
            try:
                resp = client.chat.complete(
                    model=self._model,
                    messages=messages,
                    temperature=_DEFAULT_TEMPERATURE,
                    response_format={"type": "json_object"},
                    timeout=self._timeout,
                )
                return resp.choices[0].message.content
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "[ARBITRATOR] tentative %d/%d echec : %s",
                    attempt,
                    self._max_retries + 1,
                    exc,
                )

        logger.error("[ARBITRATOR] tous les essais ont echoue : %s", last_exc)
        return None

    # ── Methode 1 : disambiguation type de document ───────────────────────

    def disambiguate_document_type(
        self,
        text: str,
        candidates: list[Any],
        deterministic_confidence: float,
    ) -> TracedField:
        """
        Disambigue le type de document quand le deterministe doute.

        Le LLM choisit parmi les candidats proposes — il ne peut pas inventer
        un type hors taxonomie. Confiance plafonnee a 0.85.

        Args:
            text: Extrait du document (max 3000 chars).
            candidates: Liste de DocumentKindParent candidats du deterministe.
            deterministic_confidence: Confiance du deterministe (contexte).

        Returns:
            TracedField(value=DocumentKindParent_or_str, confidence, evidence)
        """
        if not candidates:
            return _not_resolved("disambiguate_document_type", "no_candidates")

        candidate_values = [
            c.value if hasattr(c, "value") else str(c) for c in candidates
        ]

        system_msg = (
            "Tu es un expert senior en marches publics Afrique de l'Ouest. "
            "Tu dois identifier le type d'un document procurement. "
            "Reponds UNIQUEMENT en JSON valide avec les cles: "
            '{"type": "<valeur_choisie>", "confidence": <float 0.0-1.0>, '
            '"evidence": "<phrase courte justifiant le choix>"}. '
            "Zéro texte en dehors du JSON."
        )

        user_msg = (
            f"Extrait de document:\n\n{text[:3000]}\n\n"
            f"Candidats possibles (choisir parmi cette liste uniquement) : "
            f"{candidate_values}\n\n"
            f"Le classifieur automatique a une confiance de {deterministic_confidence:.2f}. "
            "Quel est le type le plus probable? "
            'Reponds en JSON: {"type": "...", "confidence": 0.XX, "evidence": "..."}'
        )

        raw = self._call(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ]
        )

        if not raw:
            return _not_resolved("disambiguate_document_type", "api_unavailable")

        parsed = _safe_json(raw)
        doc_type = parsed.get("type", "")
        confidence = float(parsed.get("confidence", 0.0))
        evidence_str = str(parsed.get("evidence", ""))

        # Guard taxonomie : le LLM ne peut retourner que ce qui est dans les candidats
        if doc_type not in candidate_values:
            logger.warning(
                "[ARBITRATOR] type_disambiguation : LLM a retourne '%s' hors candidats %s",
                doc_type,
                candidate_values,
            )
            return _not_resolved(
                "disambiguate_document_type",
                f"llm_returned_out_of_taxonomy:{doc_type}",
            )

        capped = _cap(confidence, self._max_conf_type)
        logger.info(
            "[ARBITRATOR] type_disambiguation : %s conf=%.2f->%.2f evidence=%s",
            doc_type,
            confidence,
            capped,
            evidence_str[:80],
        )

        return TracedField(
            value=doc_type,
            confidence=capped,
            evidence=[
                f"llm_arbitration:{self._model}",
                f"evidence:{evidence_str[:120]}",
                f"det_conf:{deterministic_confidence:.2f}",
            ],
        )

    # ── Methode 2 : detection partie obligatoire (Level 3) ────────────────

    def detect_mandatory_part(
        self,
        text_excerpt: str,
        part_name: str,
        part_description: str = "",
    ) -> TracedField:
        """
        Detecte si un extrait contient une partie obligatoire (Level 3 LLM).

        Appele quand L1 (heading) et L2 (keyword density) ont echoue.
        Confiance plafonnee a 0.70 (config mandatory_parts._defaults.yaml).

        Args:
            text_excerpt: Extrait de texte (max 2000 chars).
            part_name: Nom de la partie a detecter.
            part_description: Description contextuelle (optionnel).

        Returns:
            TracedField(value=bool, confidence, evidence)
        """
        system_msg = (
            "Tu es un expert en analyse de documents de marches publics. "
            "Reponds UNIQUEMENT en JSON: "
            '{"detected": true/false, "confidence": <float 0.0-1.0>, '
            '"evidence": "<citation courte du texte justifiant la reponse>"}. '
            "Zéro texte hors JSON."
        )

        desc_part = f" ({part_description})" if part_description else ""
        user_msg = (
            f"Extrait de document:\n\n{text_excerpt[:2000]}\n\n"
            f"Question : Ce texte contient-il la section ou partie '{part_name}'{desc_part} ? "
            'Reponds en JSON: {"detected": true/false, "confidence": 0.XX, "evidence": "..."}'
        )

        raw = self._call(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ]
        )

        if not raw:
            return _not_resolved("detect_mandatory_part", "api_unavailable")

        parsed = _safe_json(raw)
        detected_raw = parsed.get("detected")
        detected = _parse_bool_strict(detected_raw)
        if detected is None:
            logger.warning(
                "[ARBITRATOR] detect_mandatory_part '%s' : valeur 'detected' non parseable: %r",
                part_name,
                detected_raw,
            )
            return _not_resolved("detect_mandatory_part", "unparseable_bool_detected")
        confidence = float(parsed.get("confidence", 0.0))
        evidence_str = str(parsed.get("evidence", ""))

        capped = _cap(confidence, self._max_conf_parts)
        logger.info(
            "[ARBITRATOR] detect_mandatory_part '%s' : detected=%s conf=%.2f->%.2f",
            part_name,
            detected,
            confidence,
            capped,
        )

        return TracedField(
            value=detected,
            confidence=capped,
            evidence=[
                f"llm_arbitration:{self._model}",
                f"part:{part_name}",
                f"evidence:{evidence_str[:120]}",
            ],
        )

    # ── Methode 3 : lien semantique entre documents ───────────────────────

    def semantic_link_documents(
        self,
        doc_a_summary: str,
        doc_b_summary: str,
        text_a_excerpt: str = "",
        text_b_excerpt: str = "",
    ) -> TracedField:
        """
        Determine si deux documents font partie du meme processus d'achat.

        Appele par process_linker quand le fuzzy matching est insuffisant.
        Confiance plafonnee a 0.80.

        Args:
            doc_a_summary: Resume du document A (reference, type, entite, projet).
            doc_b_summary: Resume du document B.
            text_a_excerpt: Extrait texte A (optionnel, max 500 chars).
            text_b_excerpt: Extrait texte B (optionnel, max 500 chars).

        Returns:
            TracedField(value=bool, confidence, evidence)
        """
        system_msg = (
            "Tu es un expert senior en depouillements de marches publics Afrique de l'Ouest. "
            "Tu dois determiner si deux documents appartiennent au meme processus d'achat. "
            "Reponds UNIQUEMENT en JSON: "
            '{"linked": true/false, "link_nature": "<offer_to_dao|offer_to_rfq|annex_to_offer|unrelated>", '
            '"confidence": <float 0.0-1.0>, '
            '"evidence": "<justification courte>"}. '
            "Zéro texte hors JSON."
        )

        excerpts = ""
        if text_a_excerpt:
            excerpts += f"\n\nExtrait document A:\n{text_a_excerpt[:500]}"
        if text_b_excerpt:
            excerpts += f"\n\nExtrait document B:\n{text_b_excerpt[:500]}"

        user_msg = (
            f"Document A : {doc_a_summary}\n"
            f"Document B : {doc_b_summary}"
            f"{excerpts}\n\n"
            "Ces deux documents font-ils partie du meme processus d'achat? "
            'Reponds en JSON: {"linked": true/false, "link_nature": "...", '
            '"confidence": 0.XX, "evidence": "..."}'
        )

        raw = self._call(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ]
        )

        if not raw:
            return _not_resolved("semantic_link_documents", "api_unavailable")

        parsed = _safe_json(raw)
        linked_raw = parsed.get("linked")
        linked = _parse_bool_strict(linked_raw)
        if linked is None:
            logger.warning(
                "[ARBITRATOR] semantic_link_documents : valeur 'linked' non parseable: %r",
                linked_raw,
            )
            return _not_resolved("semantic_link_documents", "unparseable_bool_linked")
        link_nature = str(parsed.get("link_nature", "unrelated"))
        confidence = float(parsed.get("confidence", 0.0))
        evidence_str = str(parsed.get("evidence", ""))

        capped = _cap(confidence, self._max_conf_link)
        logger.info(
            "[ARBITRATOR] semantic_link : linked=%s nature=%s conf=%.2f->%.2f",
            linked,
            link_nature,
            confidence,
            capped,
        )

        return TracedField(
            value=linked,
            confidence=capped,
            evidence=[
                f"llm_arbitration:{self._model}",
                f"link_nature:{link_nature}",
                f"evidence:{evidence_str[:120]}",
            ],
        )
