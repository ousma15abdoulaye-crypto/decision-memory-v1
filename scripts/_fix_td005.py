"""Fix TD-005 section content in TECHNICAL_DEBT.md."""
from pathlib import Path
import re

TD = Path("TECHNICAL_DEBT.md")
content = TD.read_text(encoding="utf-8")

# Find the TD-005 section and replace the table + body up to "Propriétaire"
# The heading was already updated to FERMÉE by the previous script.
# We replace everything between the heading and "---\n\n### TD-006"

pattern = r'(### TD-005 · lazy init DATABASE_URL — FERMÉE \(réelle · 2026-03-03\)\n\n)(\|\| Attribut.*?\*\*Propriétaire :\*\* CTO · FERMÉE\.)'

replacement = r"""\1|| Attribut | Valeur |
|||---|---|
||| Statut | **FERMÉE (réelle · 2026-03-03)** |
||| Sévérité | Haute · RÉSOLUE |
||| Fichiers | `src/db/core.py` · `src/db/__init__.py` |
||| Ref ADR | ADR-M5-PRE-001 § D1.1 |

**Résolu :**
- `src/db/__init__.py` : appel eager `_get_database_url()` supprimé · M5-CLEANUP-A
- `src/db/core.py` : `_get_or_init_db_url()` · seul point d'entrée · lazy init

**Note :** précédemment fermée de façon incorrecte (core.py seulement).
`__init__.py` bypassait le cache via appel direct `_get_database_url()` à l'import.
Corrigé M5-CLEANUP-A · `python -c "import src.db"` → OK sans DATABASE_URL.
Commit bb3aa09 (core.py) + M5-CLEANUP-A (__init__.py).

**Propriétaire :** CTO · FERMÉE."""

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

if new_content == content:
    print("WARN: pattern not matched — printing surrounding context")
    idx = content.find("TD-005 · lazy init")
    print(repr(content[idx:idx+600]))
else:
    TD.write_text(new_content, encoding="utf-8")
    print("TD-005 body updated OK")
