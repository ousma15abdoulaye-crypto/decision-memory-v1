from pathlib import Path

TD = Path("TECHNICAL_DEBT.md")
content = TD.read_text(encoding="utf-8")

# The separator at line 546 has |||---|---| (3 pipes) but should be ||---|---| (2 pipes)
# to match the header || Attribut | Valeur | (2-pipe prefix)
# Only fix the one in TD-005 section (there's only one |||---|---| in the file)
fixed = content.replace("|||---|---|", "||---|---|", 1)

if fixed != content:
    TD.write_text(fixed, encoding="utf-8")
    print("Fixed: |||---|---| -> ||---|---|")
else:
    print("No change made")
