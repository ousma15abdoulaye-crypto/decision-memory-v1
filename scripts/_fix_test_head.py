f = "tests/test_m0b_db_hardening.py"
txt = open(f, encoding="utf-8").read()
old = 'row["version_num"] == "039"'
new = 'row["version_num"] == "039_created_at_timestamptz"'
old_msg = 'f"Head attendu : 039 — réel : {row[\'version_num\']}"'
new_msg = 'f"Head attendu : 039_created_at_timestamptz — réel : {row[\'version_num\']}"'
old_doc = '"""Head = 039 (head courante après M2B — migration users.created_at TIMESTAMPTZ)."""'
new_doc = '"""Head = 039_created_at_timestamptz (head courante après M2B — migration users.created_at TIMESTAMPTZ)."""'
txt = txt.replace(old, new).replace(old_msg, new_msg).replace(old_doc, new_doc)
open(f, "w", encoding="utf-8").write(txt)
print("Patched:", f)
for line in open(f, encoding="utf-8"):
    if "039" in line:
        print(" ", line.rstrip())
