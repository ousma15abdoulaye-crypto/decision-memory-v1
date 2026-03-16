# Install Railway CLI — Windows x64
# URL correcte (install.ps1 deprecated) : GitHub releases
# Usage : .\scripts\install_railway_cli.ps1

$ErrorActionPreference = "Stop"
$version = "v4.31.0"
$url = "https://github.com/railwayapp/cli/releases/download/$version/railway-$version-x86_64-pc-windows-msvc.zip"
$binDir = Join-Path $env:USERPROFILE "bin"
$zipPath = Join-Path $env:TEMP "railway-cli.zip"

Write-Host "Railway CLI — Installation Windows x64" -ForegroundColor Cyan
Write-Host "  URL: $url"
Write-Host ""

# Creer dossier
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
Write-Host "[1/4] Dossier: $binDir" -ForegroundColor Green

# Telecharger (TLS 1.2 pour GitHub)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try {
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
} catch {
    Write-Host "  ERREUR telechargement: $_" -ForegroundColor Red
    Write-Host "  Essai manuel: ouvrir $url dans le navigateur" -ForegroundColor Yellow
    exit 1
}
Write-Host "[2/4] Telechargement OK" -ForegroundColor Green

# Extraire
Expand-Archive -Path $zipPath -DestinationPath $binDir -Force
Remove-Item $zipPath -ErrorAction SilentlyContinue
Write-Host "[3/4] Extraction OK" -ForegroundColor Green

# Verifier executable (le zip contient railway.exe a la racine ou dans un sous-dossier)
$exe = Get-ChildItem -Path $binDir -Filter "railway*.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if ($exe) {
    if ($exe.DirectoryName -ne $binDir) {
        Move-Item $exe.FullName (Join-Path $binDir "railway.exe") -Force
        Get-ChildItem $exe.DirectoryName -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    } elseif ($exe.Name -ne "railway.exe") {
        Rename-Item $exe.FullName "railway.exe"
    }
}

# Ajouter au PATH utilisateur
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$sep = ";"
if ($currentPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("Path", $binDir + $sep + $currentPath, "User")
    $env:PATH = $binDir + $sep + $env:PATH
    Write-Host "[4/4] PATH mis a jour (User)" -ForegroundColor Green
} else {
    $env:PATH = $binDir + $sep + $env:PATH
    Write-Host "[4/4] PATH deja configure" -ForegroundColor Green
}

Write-Host ""
Write-Host "Installation terminee." -ForegroundColor Cyan
Write-Host "  Fermer et rouvrir le terminal, puis:" -ForegroundColor Yellow
Write-Host "    railway --version"
Write-Host "    railway login"
Write-Host ""
Write-Host "  Ou tester maintenant (session courante):" -ForegroundColor Yellow
& (Join-Path $binDir "railway.exe") --version 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  railway OK" -ForegroundColor Green
} else {
    Write-Host "  Relancer le terminal pour PATH" -ForegroundColor Yellow
}
