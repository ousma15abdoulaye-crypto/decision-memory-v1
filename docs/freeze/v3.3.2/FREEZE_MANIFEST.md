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

## Checksums

| Fichier (relatif à la racine du repo) | SHA256 |
|---------------------------------------|--------|
| docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md | eec3c2ee34cce690525161f713e054de9671e69f31d98a9316ac57fe68c55215 |
| docs/freeze/v3.3.2/MILESTONES_EXECUTION_PLAN_V3.3.2.md | b142de17aacb689d9d3baec362b5adf51bb395fe9a4854627321c61dfaaad64a |
| docs/freeze/v3.3.2/INVARIANTS.md | ddcb557ca5f1646f1bd5ca0aa2a0a1cdeb83082718131503ebd16a978c3660ef |
| docs/freeze/v3.3.2/adrs/ADR-0001.md | 323cfffc5a5935356f9cc682c2975f17ed5110d00684f187aff8081560aad537 |

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
