$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$envFile = Join-Path $repoRoot ".local\secrets\dms-production.env"

if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Error "[DMS ENV] Missing local secrets file: .local\secrets\dms-production.env"
    Write-Host "[DMS ENV] Create it locally, then load with:"
    Write-Host "[DMS ENV] . .\scripts\local\load_dms_prod_env.ps1"
    throw "DMS production env file not found"
}

foreach ($line in Get-Content -LiteralPath $envFile) {
    $trimmed = $line.Trim()
    if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) {
        continue
    }

    if ($trimmed -notmatch "^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$") {
        Write-Warning "[DMS ENV] Ignored invalid line without KEY=VALUE format"
        continue
    }

    $key = $Matches[1]
    $value = $Matches[2].Trim()

    if (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    Set-Item -Path "Env:$key" -Value $value
    Write-Host "[DMS ENV] $key loaded"
}

Write-Host "[DMS ENV] Load complete. Correct usage for persistent session env:"
Write-Host "[DMS ENV] . .\scripts\local\load_dms_prod_env.ps1"
