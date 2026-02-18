# Regenerate freeze checksums on Windows (converting CRLF to LF like Linux)
# This ensures checksums match Linux CI environment

$freezeDir = "docs\freeze\v3.3.2"
$checksumsFile = "$freezeDir\SHA256SUMS.txt"

if (-not (Test-Path $freezeDir)) {
    Write-Error "Freeze directory not found: $freezeDir"
    exit 1
}

Write-Host "Regenerating SHA256 checksums (Linux-compatible)..." -ForegroundColor Cyan

# Get all .md and .txt files except SHA256SUMS.txt and FREEZE_MANIFEST.md
$files = Get-ChildItem -Path $freezeDir -Recurse -Include *.md,*.txt | 
    Where-Object { $_.Name -ne "SHA256SUMS.txt" -and $_.Name -ne "FREEZE_MANIFEST.md" } | 
    Sort-Object FullName

$checksums = @()

foreach ($file in $files) {
    # Read file content and convert CRLF to LF (like Linux)
    $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
    $content = $content -replace "`r`n", "`n" -replace "`r", "`n"
    
    # Calculate SHA256 hash
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    $hashString = ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
    
    # Get relative path (Unix-style forward slashes)
    $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "").Replace("\", "/")
    
    $checksums += "$hashString  $relativePath"
    Write-Host "  $relativePath" -ForegroundColor Gray
}

# Write checksums file (with LF line endings)
$checksumsContent = ($checksums -join "`n") + "`n"
[System.IO.File]::WriteAllText($checksumsFile, $checksumsContent, [System.Text.Encoding]::UTF8)

Write-Host "`n✅ SHA256SUMS.txt regenerated" -ForegroundColor Green
Write-Host "`nChecksums:" -ForegroundColor Cyan
$checksums | ForEach-Object { Write-Host $_ }
