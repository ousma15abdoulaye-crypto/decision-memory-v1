# MN-ENV-SETUP-T14-GEN13 — verification rapide de l'environnement DMS
$ErrorActionPreference = "Continue"
Write-Host "=== DMS ENV CHECK ===" -ForegroundColor Cyan

$checks = [ordered]@{
    "Python"    = "python --version"
    "Git"       = "git --version"
    "Docker"    = "docker --version"
    "Railway"   = "railway --version"
    "Tesseract" = "tesseract --version"
    "AWS CLI"   = "aws --version"
    "Node"      = "node --version"
}

foreach ($name in $checks.Keys) {
    try {
        $result = Invoke-Expression $checks[$name] 2>&1 | Out-String
        $result = $result.Trim()
        if ($LASTEXITCODE -ne 0 -and -not $result) { throw "exit $LASTEXITCODE" }
        Write-Host "OK $name : $result" -ForegroundColor Green
    }
    catch {
        Write-Host "FAIL $name : NON INSTALLE OU ABSENT DU PATH" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== DOCKER CONTAINERS ===" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
