# Sauvegarder comme : extract_for_ls.py
# Exécuter : python extract_for_ls.py
# Fichiers : scripts/ ou data/imports/imc/

import json
import os

from pdfminer.high_level import extract_text
import openpyxl

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
IMC_DIR = os.path.join(PROJECT_ROOT, "data", "imports", "imc")


def _find(paths):
    """Premier chemin existant."""
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


tasks = []

# doc_type_hint → document_role pour /predict (task_data.document_role) — LOI 1bis
_HINT_TO_ROLE = {
    "dao": "dao",
    "tdr_consultance_audit": "tdr_consultance_audit",
    "rfq": "rfq",
}


def _task_row(text: str, source: str, doc_type_hint: str) -> dict:
    return {
        "text": text,
        "source": source,
        "doc_type_hint": doc_type_hint,
        "document_role": _HINT_TO_ROLE.get(doc_type_hint, doc_type_hint),
    }


# Doc 1 — ITT DAO (ou PDF imc en fallback)
path1 = _find(
    [
        os.path.join(
            SCRIPT_DIR, "ITT_MPT_-LOT-2-FOURNITURE-MATERIELS-CONSOMMABLES.pdf"
        ),
        os.path.join(IMC_DIR, "AOUT18.pdf"),
    ]
)
try:
    if path1:
        text1 = extract_text(path1)
        tasks.append(
            _task_row(
                text1[:8000],
                "ITT_MPT_LOT2" if "ITT" in path1 else "IMC_AOUT18",
                "dao",
            )
        )
        print(f"[OK] Doc1 : {len(text1)} chars ({os.path.basename(path1)})")
    else:
        print("[KO] Doc1 : fichier non trouve")
except Exception as e:
    print(f"[KO] Doc1 : {e}")

# Doc 2 — TdR RFP (ou PDF imc en fallback)
path2 = _find(
    [
        os.path.join(SCRIPT_DIR, "TdR_Evaluation-de-Base_PADEM-VF-20032025_AT-YD.pdf"),
        os.path.join(IMC_DIR, "AOUT19.pdf"),
    ]
)
try:
    if path2:
        text2 = extract_text(path2)
        tasks.append(
            _task_row(
                text2[:8000],
                "TdR_PADEM" if "TdR" in path2 else "IMC_AOUT19",
                "tdr_consultance_audit",
            )
        )
        print(f"[OK] Doc2 : {len(text2)} chars ({os.path.basename(path2)})")
    else:
        print("[KO] Doc2 : fichier non trouve")
except Exception as e:
    print(f"[KO] Doc2 : {e}")

# Doc 3 — RFQ Excel (optionnel)
path3 = _find(
    [
        os.path.join(SCRIPT_DIR, "RFQ_Impression-de-goodies-personnalises_Lot1.xlsx"),
        os.path.join(PROJECT_ROOT, "RFQ_Impression-de-goodies-personnalises_Lot1.xlsx"),
    ]
)
try:
    if path3:
        wb = openpyxl.load_workbook(path3)
        rows = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                line = " | ".join(str(c) for c in row if c is not None)
                if line.strip():
                    rows.append(line)
        text3 = "\n".join(rows)
        tasks.append(_task_row(text3[:8000], "RFQ_Goodies_Lot1", "rfq"))
        print(f"[OK] Doc3 : {len(text3)} chars ({os.path.basename(path3)})")
    else:
        print("[KO] Doc3 : RFQ xlsx non trouve (optionnel)")
except Exception as e:
    print(f"[KO] Doc3 : {e}")

# Export JSON (métadonnées + texte — rétrocompat)
out_path = os.path.join(SCRIPT_DIR, "ls_import.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

# Format import direct Label Studio : une entrée = { "data": { ... } }
ls_wrapped = [
    {
        "data": {
            "text": t["text"],
            "document_role": t.get("document_role", ""),
            "source": t.get("source", ""),
        }
    }
    for t in tasks
]
out_ls = os.path.join(SCRIPT_DIR, "ls_tasks_labelstudio.json")
with open(out_ls, "w", encoding="utf-8") as f:
    json.dump(ls_wrapped, f, ensure_ascii=False, indent=2)

print(f"\n[OK] ls_import.json — {len(tasks)} taches ({out_path})")
print(f"[OK] ls_tasks_labelstudio.json — import LS ({out_ls})")
if tasks:
    print("-> Apercu premiere tache (LS) :")
    print(json.dumps(ls_wrapped[0], ensure_ascii=False)[:220])
