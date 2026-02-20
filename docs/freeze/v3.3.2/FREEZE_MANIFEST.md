# Freeze manifest — V3.3.2

## Identité

| Champ | Valeur |
|-------|--------|
| **Version** | 3.3.2 |
| **Date / heure** | 2026-02-16 16:11:08 Europe/London (+01:00) |
| **Autorité** | Tech Lead DMS (Abdoulaye Ousmane) |

## Scope — Fichiers freezés

- `docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md`
- `docs/freeze/v3.3.2/MILESTONES_EXECUTION_PLAN_V3.3.2.md`
- `docs/freeze/v3.3.2/INVARIANTS.md`
- `docs/freeze/v3.3.2/adrs/ADR-0001.md`
- `docs/freeze/v3.3.2/adrs/ADR-0004.md`

## Checksums

| Fichier (relatif à la racine du repo) | SHA256 |
|---------------------------------------|--------|
| docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md | 7695cc523e67ab53722f97ff36d979eb0e0c832d54c5d4de1b9a6df5ddd82549 |
| docs/freeze/v3.3.2/MILESTONES_EXECUTION_PLAN_V3.3.2.md | 90b64e0b155aa544a42d6161957f875061cb1fbc9197402124d3aacd5516489e |
| docs/freeze/v3.3.2/INVARIANTS.md | fe32fc0485afc303ab8508b8e5369e908f94106d71fb9eca48a12602b9bfda54 |
| docs/freeze/v3.3.2/adrs/ADR-0001.md | e3a32be97e3c6a3b0e17a73ce581b8de806f488d9ab12f3962804833829688f0 |
| docs/freeze/v3.3.2/adrs/ADR-0004.md | 3add6013efd74a3cd58bcf15d1aa71801fd4941858c4200217be2fa18bb0c8b3 |

Référence complète : `docs/freeze/v3.3.2/SHA256SUMS.txt`.

## Procédure de vérification

### Windows (PowerShell)

Depuis la racine du repo :

```powershell
# Option 1 : script fourni
.\scripts\freeze\verify_freeze_v3.3.2.ps1

# Option 2 : manuel
$sums = Get-Content docs\freeze\v3.3.2\SHA256SUMS.txt
foreach ($line in $sums) {
  if ($line -match '^([a-f0-9]{64})\s{2}(.+)$') {
    $hash = $1; $path = $2 -replace '/','\'
    $current = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($current -ne $hash) { Write-Error "MISMATCH: $path" }
  }
}
```

### Linux / CI

Depuis la racine du repo :

```bash
sha256sum -c docs/freeze/v3.3.2/SHA256SUMS.txt
```

Sortie attendue : `OK` pour chaque ligne (ou message d’erreur en cas de divergence).

## Règle d’opposabilité

Toute modification du contenu freezé (constitution, milestones, invariants, ADR) entraîne une **nouvelle version** (ex. v3.3.3) et un **nouveau freeze** : nouvel répertoire `docs/freeze/v3.3.x/`, nouveau SHA256SUMS.txt et mise à jour du présent manifeste. Les répertoires freezés existants ne sont pas modifiés.
