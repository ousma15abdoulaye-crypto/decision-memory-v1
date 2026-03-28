#!/usr/bin/env python3
"""
Import réglementaire — extraction texte (LlamaParse / Mistral OCR / local)
puis structuration JSON via Mistral chat (bibliothèque DMS).

Usage (racine du dépôt) :
  python scripts/parse_regulatory_docs.py --all --method auto
  python scripts/parse_regulatory_docs.py --file data/regulatory/raw/sci_manual.pdf

Variables : MISTRAL_API_KEY ; optionnel LLAMADMS / LLAMA_CLOUD_API_KEY (LlamaParse).

Ne pas utiliser en CI avec clés réelles (RÈGLE-21) — réservé mandat local / AO.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Monorepo : racine = parent de scripts/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _load_dotenv() -> None:
    """Charge .env puis .env.local (override) depuis la racine du dépôt."""
    try:
        from dotenv import load_dotenv

        env_f = _ROOT / ".env"
        local_f = _ROOT / ".env.local"
        if env_f.is_file():
            load_dotenv(env_f)
        if local_f.is_file():
            load_dotenv(local_f, override=True)
    except ImportError:
        pass


def _load_mistral_key_from_simple_file() -> None:
    """Lit data/regulatory/MISTRAL_KEY.txt (une ligne) et définit MISTRAL_API_KEY.

    Priorité **après** .env : si le fichier existe avec une ligne non vide, il remplace
    la variable (cas utilisateur : clé à jour dans le fichier, ancienne clé dans .env).
    """
    key_path = _ROOT / "data" / "regulatory" / "MISTRAL_KEY.txt"
    if not key_path.is_file():
        return
    for line in key_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            os.environ["MISTRAL_API_KEY"] = line
            return


def _load_env_for_run() -> None:
    _load_dotenv()
    _load_mistral_key_from_simple_file()


def _mistral_key_ok() -> bool:
    return bool(os.environ.get("MISTRAL_API_KEY", "").strip())


def _print_mistral_key_help() -> None:
    key_txt = _ROOT / "data" / "regulatory" / "MISTRAL_KEY.txt"
    print(
        "Cle Mistral introuvable.\n\n"
        "  SIMPLE : cree ce fichier texte (une seule ligne = ta cle) :\n"
        f"    {key_txt}\n\n"
        "  OU dans .env.local : MISTRAL_API_KEY=sk-...\n"
        f"  (exemple : {_ROOT / 'data' / 'regulatory' / 'MISTRAL_KEY.txt.example'})",
        file=sys.stderr,
    )


STRUCTURING_SYSTEM_PROMPT = """Tu es un analyste procurement senior. Tu reçois le texte extrait d'un document réglementaire (manuel SCI interne OU code marchés publics Mali / DGMP).
Produis UN objet JSON valide (pas de markdown) avec cette structure exacte :
{
  "document_kind": "sci_manual" | "dgmp_code" | "arrete" | "other",
  "title_guess": "string ou null",
  "language": "fr" | "en" | "mixed",
  "sections": [ { "heading": "string", "summary": "string", "verbatim_citations": ["courtes citations"] } ],
  "thresholds": [ { "label": "string", "currency": "USD" | "XOF" | "FCFA" | "unknown", "min": number|null, "max": number|null, "procedure": "string|null", "notes": "string|null" } ],
  "procedures": [ { "name": "string", "description": "string", "conditions": "string|null" } ],
  "committee_rules": [ { "context": "string", "composition": "string", "quorum": "string|null" } ],
  "evaluation_criteria": [ { "criterion": "string", "weight_rule": "string|null", "eliminatory": true|false|null } ],
  "unresolved_or_ambiguous": [ "points nécessitant validation humaine" ],
  "confidence_notes": "string — limites de ce parsing automatique"
}
Si une information est absente, utilise des tableaux vides ou null. Ne invente pas de chiffres : si le texte est flou, mets l'entrée dans unresolved_or_ambiguous."""


def _guess_label(path: Path) -> str:
    name = path.name.lower()
    if "sci" in name or "save" in name or "children" in name:
        return "sci"
    if "dgmp" in name or "mali" in name or "marche" in name or "public" in name:
        return "dgmp"
    return "unknown"


def _extract_text_local_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts).strip()


def _extract_text_local_docx(path: Path) -> str:
    from src.extraction.engine import _extract_docx

    raw, _ = _extract_docx(str(path))
    return raw.strip()


def _extract_text_mistral_ocr(path: Path) -> str:
    from src.extraction.engine import _extract_mistral_ocr

    raw, _ = _extract_mistral_ocr(str(path))
    return raw.strip()


def _extract_text_llamaparse(path: Path) -> str:
    from src.extraction.engine import _extract_llamaparse

    raw, _ = _extract_llamaparse(str(path))
    return raw.strip()


def _extract_auto(path: Path) -> tuple[str, str]:
    """Retourne (texte, méthode_utilisée)."""
    suf = path.suffix.lower()
    if suf == ".docx":
        return _extract_text_local_docx(path), "docx_local"
    if suf == ".pdf":
        local = _extract_text_local_pdf(path)
        if len(local) >= 80:
            return local, "pypdf_native"
        return _extract_text_mistral_ocr(path), "mistral_ocr"
    raise ValueError(f"Extension non supportée : {suf} (utiliser .pdf ou .docx)")


def _structure_with_mistral(text: str, source_label: str) -> dict:
    """Appel Mistral chat — JSON structuré."""
    try:
        from mistralai.client import Mistral
    except ImportError:
        from mistralai import Mistral  # type: ignore

    from src.core.api_keys import get_mistral_api_key
    from src.extraction.engine import mistral_httpx_client

    api_key = get_mistral_api_key()
    client = Mistral(api_key=api_key, client=mistral_httpx_client())
    model = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
    user_preview = text[:120_000]
    if len(text) > 120_000:
        user_preview += "\n\n[... texte tronqué pour le modèle ; taille totale = " + str(len(text)) + " caractères ]"

    resp = client.chat.complete(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": STRUCTURING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Source détectée : {source_label}. Texte du document :\n\n{user_preview}",
            },
        ],
        response_format={"type": "json_object"},
    )
    raw = (resp.choices[0].message.content or "").strip()
    return json.loads(raw)


def _write_extracted_md(path: Path, text: str, method: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"---\nextracted_at: {datetime.now(UTC).isoformat()}\nmethod: {method}\n---\n\n"
    path.write_text(header + text, encoding="utf-8")


def process_one(
    raw_path: Path,
    *,
    method: str,
    extract_only: bool,
) -> int:
    raw_path = raw_path.resolve()
    if not raw_path.is_file():
        print(f"[ERR] Fichier absent : {raw_path}", file=sys.stderr)
        return 1

    stem = raw_path.stem
    out_dir = _ROOT / "data" / "regulatory" / "parsed"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{stem}_extracted.md"
    json_path = out_dir / f"{stem}_library.json"

    label = _guess_label(raw_path)

    try:
        if method == "auto":
            text, used = _extract_auto(raw_path)
        elif method == "mistral_ocr":
            text = _extract_text_mistral_ocr(raw_path)
            used = "mistral_ocr"
        elif method == "llamaparse":
            text = _extract_text_llamaparse(raw_path)
            used = "llamaparse"
        else:
            print(f"[ERR] Méthode inconnue : {method}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"[ERR] Extraction échouée ({raw_path.name}) : {exc}", file=sys.stderr)
        return 1

    _write_extracted_md(md_path, text, used)
    print(f"[OK] Extrait -> {md_path} ({used}, {len(text)} car.)")

    if extract_only:
        return 0

    try:
        structured = _structure_with_mistral(text, label)
    except Exception as exc:
        print(f"[ERR] Structuration LLM échouée : {exc}", file=sys.stderr)
        return 1

    try:
        src_rel = str(raw_path.relative_to(_ROOT))
    except ValueError:
        src_rel = str(raw_path)

    envelope = {
        "dms_regulatory_library_version": "1.0.0",
        "source_file": src_rel,
        "source_label_guess": label,
        "extracted_at": datetime.now(UTC).isoformat(),
        "extraction_method": used,
        "text_char_length": len(text),
        "text_preview": text[:4000] + ("..." if len(text) > 4000 else ""),
        "structured": structured,
    }
    json_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] Bibliotheque -> {json_path}")
    return 0


def main() -> int:
    _load_env_for_run()

    # engine._validate_storage_uri exige STORAGE_BASE_PATH ; défaut /tmp exclut le repo Windows
    _prev_storage = os.environ.get("STORAGE_BASE_PATH")
    os.environ["STORAGE_BASE_PATH"] = str(_ROOT)

    try:
        ap = argparse.ArgumentParser(description="Parse reglementaire SCI / DGMP vers DMS")
        ap.add_argument(
            "--file",
            type=Path,
            help="Un fichier dans data/regulatory/raw/ (PDF ou DOCX)",
        )
        ap.add_argument(
            "--all",
            action="store_true",
            help="Traiter tous les PDF/DOCX de data/regulatory/raw/",
        )
        ap.add_argument(
            "--method",
            choices=("auto", "mistral_ocr", "llamaparse"),
            default="auto",
            help="auto = PDF natif pypdf puis OCR si vide ; DOCX local",
        )
        ap.add_argument(
            "--extract-only",
            action="store_true",
            help="Ne pas appeler Mistral chat pour la structuration JSON",
        )
        args = ap.parse_args()

        if args.method == "mistral_ocr" and not _mistral_key_ok():
            _print_mistral_key_help()
            return 2
        if not args.extract_only and not _mistral_key_ok():
            _print_mistral_key_help()
            return 2

        raw_dir = _ROOT / "data" / "regulatory" / "raw"

        if args.all:
            files = sorted(
                p
                for p in raw_dir.iterdir()
                if p.is_file() and p.suffix.lower() in (".pdf", ".docx")
            )
            if not files:
                print(f"[WARN] Aucun PDF/DOCX dans {raw_dir}")
                return 0
            rc = 0
            for f in files:
                r = process_one(f, method=args.method, extract_only=args.extract_only)
                if r != 0:
                    rc = r
            return rc

        if args.file:
            return process_one(args.file, method=args.method, extract_only=args.extract_only)

        ap.print_help()
        return 1
    finally:
        if _prev_storage is None:
            os.environ.pop("STORAGE_BASE_PATH", None)
        else:
            os.environ["STORAGE_BASE_PATH"] = _prev_storage


if __name__ == "__main__":
    raise SystemExit(main())
