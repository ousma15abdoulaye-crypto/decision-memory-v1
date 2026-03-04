content = open("TECHNICAL_DEBT.md", encoding="utf-8").read()
checks = [
    ("TD-005 FERMEE reelle", "FERMÉE (réelle · 2026-03-03)" in content),
    ("TD-005 __init__.py", "src/db/__init__.py" in content and "appel eager" in content),
    ("TD-011 extract_dao", "TD-011 · extract_dao_criteria_structured stub" in content),
    ("TD-012 SELECT*", "TD-012 · SELECT * persistant hors vendors" in content),
    ("TD-013 SLA-B", "TD-013 · SLA-B LlamaParse" in content),
    ("TD-014 migration017", "TD-014 · Migration 017 supprimée" in content),
    ("TD-015 append-only", "TD-015 · Protection append-only" in content),
    ("TD-016 chk_vendor", "TD-016 · Contrainte chk_vendor_id_format" in content),
    ("OLD TD-011 gone", "TD-011 · Protection append-only" not in content),
    ("OLD TD-012 gone", "TD-012 · Contrainte chk_vendor_id_format" not in content),
]
all_ok = True
for label, ok in checks:
    status = "OK" if ok else "FAIL"
    print(status + " · " + label)
    if not ok:
        all_ok = False
print("ALL OK" if all_ok else "SOME FAILURES")
