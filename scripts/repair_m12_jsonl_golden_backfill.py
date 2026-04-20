"""
Reparation structurelle des lignes m12-v2 dont ``dms_annotation`` est absent (perte LS / JSON vide).

Ne restaure PAS le contenu d'annotation disparu dans Label Studio : injecte le JSON DMS de reference
du depot (CI golden) + marqueurs d'ambiguite, puis reconstruit la ligne via
``ls_annotation_to_m12_v2_line`` (meme QA que l'export officiel).

Reference « formule » DMS valide :
  - ``data/annotations/fixtures/golden_dms_line.jsonl`` (1 objet JSON par ligne, schéma v3.0.1d)
  - Tests : ``services/annotation-backend/tests/test_schema_validator.py`` → ``_minimal_valid()``
  - Squelette « tout ABSENT » (parse/API KO) : ``backend._build_fallback_response()`` (lourd à importer)

Apres generation du JSONL repare :
  - re-importer vers R2 (PutObject meme cle) ou workflow CTO ;
  - repasser les taches en revue humaine / re-predict Mistral sur ``source_text`` pour du contenu reel.

Usage :
  python scripts/repair_m12_jsonl_golden_backfill.py \\
    --input data/annotations/m12_corpus_authoritative.jsonl \\
    --output data/annotations/m12_corpus_authoritative_repaired.jsonl

  # Aussi les lignes avec dms_annotation deja present mais export_ok false :
  python scripts/repair_m12_jsonl_golden_backfill.py -i in.jsonl -o out.jsonl --also-export-not-ok
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_ANNOTATION_BACKEND) not in sys.path:
    sys.path.insert(0, str(_ANNOTATION_BACKEND))

from m12_export_line import ls_annotation_to_m12_v2_line  # noqa: E402

from prompts.schema_validator import DMSAnnotation  # noqa: E402

GOLDEN_REL = Path("data/annotations/fixtures/golden_dms_line.jsonl")
AMBIG_LOSS = "AMBIG-R2_LS_SESSION_LOSS"


def _load_golden_template(repo_root: Path) -> dict:
    p = repo_root / GOLDEN_REL
    if not p.is_file():
        raise FileNotFoundError(f"Golden DMS introuvable : {p}")
    line = p.read_text(encoding="utf-8").splitlines()[0].strip()
    return json.loads(line)


def _choice_result(from_name: str, choice: str) -> dict:
    return {"from_name": from_name, "value": {"choices": [choice]}}


def _textarea_result(from_name: str, text: str) -> dict:
    return {"from_name": from_name, "value": {"text": [text]}}


def _synthetic_annotation(
    *,
    ann_id: int,
    dms_dump: str,
    status: str,
    attest_yes: bool,
) -> dict:
    results: list[dict] = [
        _textarea_result("extracted_json", dms_dump),
        _choice_result("annotation_status", status),
        _choice_result("routing_ok", "yes"),
        _choice_result("financial_ok", "yes"),
    ]
    if attest_yes:
        results.append(_choice_result("evidence_attestation", "yes"))
        results.append(_choice_result("no_invented_numbers", "yes"))
    return {"id": ann_id, "result": results}


def _needs_repair(line: dict, also_export_not_ok: bool) -> bool:
    if line.get("export_schema_version") != "m12-v2":
        return False
    dms = line.get("dms_annotation")
    if dms is None:
        return True
    if also_export_not_ok and line.get("export_ok") is False:
        return True
    return False


def _prepare_dms_from_golden(golden: dict) -> dict:
    d = copy.deepcopy(golden)
    amb = list(d.get("ambiguites") or [])
    if AMBIG_LOSS not in amb:
        amb.append(AMBIG_LOSS)
    d["ambiguites"] = amb
    meta = d.get("_meta")
    if not isinstance(meta, dict):
        meta = {}
        d["_meta"] = meta
    meta["review_required"] = True
    meta["annotation_status"] = "review_required"
    validated = DMSAnnotation.model_validate(d)
    return validated.model_dump(by_alias=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill dms_annotation (golden CI) pour lignes m12-v2 cassées"
    )
    parser.add_argument("--input", "-i", type=Path, required=True)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument(
        "--also-export-not-ok",
        action="store_true",
        help="Re-ecrit aussi les lignes avec dms_annotation mais export_ok=false",
    )
    parser.add_argument(
        "--status-after-repair",
        type=str,
        default="review_required",
        help="Valeur LS annotation_status après réparation (défaut: review_required)",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"STOP input introuvable : {args.input}", file=sys.stderr)
        return 2

    golden_base = _load_golden_template(_PROJECT_ROOT)
    dms_filled = _prepare_dms_from_golden(golden_base)
    dms_json = json.dumps(dms_filled, ensure_ascii=False)

    repaired = 0
    kept = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with (
        args.input.open(encoding="utf-8") as fin,
        args.output.open("w", encoding="utf-8") as fout,
    ):
        for raw in fin:
            raw = raw.strip()
            if not raw:
                continue
            line = json.loads(raw)
            if not _needs_repair(line, args.also_export_not_ok):
                fout.write(json.dumps(line, ensure_ascii=False) + "\n")
                kept += 1
                continue

            lm = line.get("ls_meta") if isinstance(line.get("ls_meta"), dict) else {}
            task_id = lm.get("task_id")
            ann_id = lm.get("annotation_id")
            project_id = lm.get("project_id")
            if task_id is None or ann_id is None or project_id is None:
                print(
                    f"STOP ls_meta incomplet task_id={task_id} ann={ann_id} proj={project_id}",
                    file=sys.stderr,
                )
                return 2

            task = {
                "id": task_id,
                "data": {"text": line.get("source_text") or ""},
            }
            ann = _synthetic_annotation(
                ann_id=int(ann_id),
                dms_dump=dms_json,
                status=args.status_after_repair,
                attest_yes=True,
            )
            new_line = ls_annotation_to_m12_v2_line(
                ann,
                task,
                int(project_id),
                enforce_validated_qa=False,
                require_ls_attestations=False,
            )
            fout.write(json.dumps(new_line, ensure_ascii=False) + "\n")
            repaired += 1

    print(
        f"Repare {repaired} ligne(s), copie {kept} inchangée(s) -> {args.output} "
        f"(template {GOLDEN_REL})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
