# Verify freeze v3.3.2 — SHA256 checksums
# Run from repo root: .\scripts\freeze\verify_freeze_v3.3.2.ps1
# Or from anywhere: & "$PSScriptRoot\verify_freeze_v3.3.2.ps1" (requires repo root as cwd or passed)

param(
    [string]$RepoRoot = (Get-Location).Path
)

$sumsPath = Join-Path $RepoRoot "docs\freeze\v3.3.2\SHA256SUMS.txt"
if (-not (Test-Path -LiteralPath $sumsPath)) {
    Write-Error "SHA256SUMS.txt not found: $sumsPath (run from repo root or set -RepoRoot)"
    exit 1
}

$lines = Get-Content -LiteralPath $sumsPath -Encoding UTF8
$failed = 0
foreach ($line in $lines) {
    $line = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line -match '^([a-f0-9]{64})\s{2}(.+)$') {
        $expectedHash = $matches[1].ToLowerInvariant()
        $relPath      = $matches[2] -replace '/', [IO.Path]::DirectorySeparatorChar
        $absPath     = Join-Path $RepoRoot $relPath
        if (-not (Test-Path -LiteralPath $absPath)) {
            Write-Warning "MISSING: $relPath"
            $failed++
            continue
        }
        $actualHash = (Get-FileHash -LiteralPath $absPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHash) {
            Write-Warning "MISMATCH: $relPath (expected $expectedHash, got $actualHash)"
            $failed++
        } else {
            Write-Host "OK  $relPath"
        }
    }
}

if ($failed -gt 0) {
    Write-Error "Verification failed: $failed file(s)"
    exit 1
}
Write-Host "All checksums verified."
exit 0
