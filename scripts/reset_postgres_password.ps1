# Script pour réinitialiser le mot de passe PostgreSQL
# Usage: powershell -ExecutionPolicy Bypass -File scripts\reset_postgres_password.ps1

param(
    [string]$NewPassword = "Babayaga02022",
    [string]$PostgresUser = "postgres"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Reinitialisation du mot de passe PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Trouver le service PostgreSQL
$service = Get-Service | Where-Object { $_.Name -like "*postgresql*" }
if (-not $service) {
    Write-Host "[ERREUR] Service PostgreSQL non trouve" -ForegroundColor Red
    Write-Host "Services disponibles:" -ForegroundColor Yellow
    Get-Service | Where-Object { $_.DisplayName -like "*postgres*" } | Select-Object Name, DisplayName
    exit 1
}

Write-Host "[OK] Service trouve: $($service.Name)" -ForegroundColor Green

# Trouver le répertoire de données PostgreSQL
$dataDir = $null
$possiblePaths = @(
    "C:\Program Files\PostgreSQL\15\data",
    "C:\Program Files\PostgreSQL\14\data",
    "C:\Program Files\PostgreSQL\13\data",
    "C:\Program Files (x86)\PostgreSQL\15\data"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $dataDir = $path
        break
    }
}

if (-not $dataDir) {
    Write-Host "[ERREUR] Repertoire de donnees PostgreSQL non trouve" -ForegroundColor Red
    Write-Host "Cherche dans: $($possiblePaths -join ', ')" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Repertoire de donnees: $dataDir" -ForegroundColor Green

$pgHbaPath = Join-Path $dataDir "pg_hba.conf"
if (-not (Test-Path $pgHbaPath)) {
    Write-Host "[ERREUR] Fichier pg_hba.conf non trouve: $pgHbaPath" -ForegroundColor Red
    exit 1
}

# Sauvegarder le fichier original
$backupPath = "$pgHbaPath.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $pgHbaPath $backupPath
Write-Host "[OK] Backup cree: $backupPath" -ForegroundColor Green

# Lire le contenu
$content = Get-Content $pgHbaPath

# Modifier pg_hba.conf pour permettre les connexions trust (temporairement)
$modified = $false
$newContent = @()
foreach ($line in $content) {
    if ($line -match "^#?\s*(host|local)\s+all\s+all\s+.*$" -and $line -notmatch "^#") {
        # Remplacer par trust pour IPv4
        if ($line -match "host\s+all\s+all\s+127\.0\.0\.1/32") {
            $newContent += "host    all             all             127.0.0.1/32            trust"
            $modified = $true
        }
        elseif ($line -match "host\s+all\s+all\s+::1/128") {
            $newContent += "host    all             all             ::1/128                 trust"
            $modified = $true
        }
        elseif ($line -match "local\s+all\s+all\s+.*") {
            $newContent += "local   all             all                                     trust"
            $modified = $true
        }
        else {
            $newContent += $line
        }
    }
    else {
        $newContent += $line
    }
}

if (-not $modified) {
    # Ajouter les lignes si elles n'existent pas
    $newContent += ""
    $newContent += "# Temporaire pour reset password"
    $newContent += "host    all             all             127.0.0.1/32            trust"
    $newContent += "host    all             all             ::1/128                 trust"
    $newContent += "local   all             all                                     trust"
}

# Écrire le fichier modifié
$newContent | Set-Content $pgHbaPath -Encoding UTF8
Write-Host "[OK] pg_hba.conf modifie (mode trust temporaire)" -ForegroundColor Green

# Redémarrer PostgreSQL
Write-Host "[*] Redemarrage de PostgreSQL..." -ForegroundColor Cyan
Restart-Service -Name $service.Name -Force
Start-Sleep -Seconds 3

# Vérifier que le service est démarré
$service = Get-Service -Name $service.Name
if ($service.Status -ne "Running") {
    Write-Host "[ERREUR] PostgreSQL n'a pas demarre" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] PostgreSQL redemarre" -ForegroundColor Green

# Trouver psql
$psqlPath = $null
$possiblePsqlPaths = @(
    "C:\Program Files\PostgreSQL\15\bin\psql.exe",
    "C:\Program Files\PostgreSQL\14\bin\psql.exe",
    "C:\Program Files\PostgreSQL\13\bin\psql.exe"
)

foreach ($path in $possiblePsqlPaths) {
    if (Test-Path $path) {
        $psqlPath = $path
        break
    }
}

if (-not $psqlPath) {
    Write-Host "[ERREUR] psql.exe non trouve" -ForegroundColor Red
    exit 1
}

Write-Host "[*] Changement du mot de passe..." -ForegroundColor Cyan

# Changer le mot de passe
$sqlCommand = "ALTER USER $PostgresUser WITH PASSWORD '$NewPassword';"
& $psqlPath -h localhost -p 5432 -U $PostgresUser -d postgres -c $sqlCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Mot de passe change avec succes!" -ForegroundColor Green
} else {
    Write-Host "[ERREUR] Echec du changement de mot de passe" -ForegroundColor Red
    Write-Host "Restauration du backup..." -ForegroundColor Yellow
    Copy-Item $backupPath $pgHbaPath -Force
    Restart-Service -Name $service.Name -Force
    exit 1
}

# Restaurer pg_hba.conf
Write-Host "[*] Restauration de pg_hba.conf..." -ForegroundColor Cyan
Copy-Item $backupPath $pgHbaPath -Force

# Redémarrer PostgreSQL
Write-Host "[*] Redemarrage final de PostgreSQL..." -ForegroundColor Cyan
Restart-Service -Name $service.Name -Force
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUCCES!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Mot de passe PostgreSQL reinitialise:" -ForegroundColor Green
Write-Host "  Utilisateur: $PostgresUser" -ForegroundColor White
Write-Host "  Mot de passe: $NewPassword" -ForegroundColor White
Write-Host ""
Write-Host "Tu peux maintenant creer la base avec:" -ForegroundColor Cyan
Write-Host "  python scripts\setup_db_with_password.py --password $NewPassword" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
