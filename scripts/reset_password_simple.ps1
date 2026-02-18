# Script simple pour réinitialiser le mot de passe PostgreSQL
# À EXÉCUTER EN TANT QU'ADMINISTRATEUR !
# Clic droit sur PowerShell → Exécuter en tant qu'administrateur

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Reinitialisation mot de passe PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: Ce script doit etre execute en tant qu'Administrateur!" -ForegroundColor Yellow
Write-Host ""

$serviceName = "postgresql-x64-15"
$dataDir = "C:\Program Files\PostgreSQL\15\data"
$pgHbaPath = "$dataDir\pg_hba.conf"
$psqlPath = "C:\Program Files\PostgreSQL\15\bin\psql.exe"
$newPassword = "Babayaga02022"

# Vérifier les permissions admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERREUR] Ce script doit etre execute en tant qu'Administrateur!" -ForegroundColor Red
    Write-Host "Clic droit sur PowerShell → Exécuter en tant qu'administrateur" -ForegroundColor Yellow
    exit 1
}

# Étape 1 : Arrêter PostgreSQL
Write-Host "[1/7] Arret de PostgreSQL..." -ForegroundColor Cyan
Stop-Service -Name $serviceName -Force
Start-Sleep -Seconds 2
Write-Host "[OK] PostgreSQL arrete" -ForegroundColor Green

# Étape 2 : Backup pg_hba.conf
Write-Host "[2/7] Backup de pg_hba.conf..." -ForegroundColor Cyan
$backupPath = "$pgHbaPath.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $pgHbaPath $backupPath -Force
Write-Host "[OK] Backup: $backupPath" -ForegroundColor Green

# Étape 3 : Modifier pg_hba.conf (trust temporaire)
Write-Host "[3/7] Modification de pg_hba.conf (mode trust)..." -ForegroundColor Cyan
$content = Get-Content $pgHbaPath
$newContent = @()
$modified = $false

foreach ($line in $content) {
    if ($line -match "^#?\s*(host|local)\s+all\s+all\s+.*(scram-sha-256|md5|password).*$" -and $line -notmatch "^#") {
        $newLine = $line -replace "(scram-sha-256|md5|password)", "trust"
        $newContent += $newLine
        $modified = $true
    } else {
        $newContent += $line
    }
}

if (-not $modified) {
    Write-Host "[WARN] Aucune ligne modifiee, ajout de lignes trust..." -ForegroundColor Yellow
    $newContent += ""
    $newContent += "# Temporaire pour reset password"
    $newContent += "host    all             all             127.0.0.1/32            trust"
    $newContent += "host    all             all             ::1/128                 trust"
    $newContent += "local   all             all                                     trust"
}

$newContent | Set-Content $pgHbaPath -Encoding UTF8
Write-Host "[OK] pg_hba.conf modifie" -ForegroundColor Green

# Étape 4 : Redémarrer PostgreSQL
Write-Host "[4/7] Redemarrage de PostgreSQL..." -ForegroundColor Cyan
Start-Service -Name $serviceName
Start-Sleep -Seconds 3
Write-Host "[OK] PostgreSQL redemarre" -ForegroundColor Green

# Étape 5 : Changer le mot de passe
Write-Host "[5/7] Changement du mot de passe..." -ForegroundColor Cyan
& $psqlPath -h localhost -p 5432 -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD '$newPassword';"

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Mot de passe change!" -ForegroundColor Green
} else {
    Write-Host "[ERREUR] Echec du changement de mot de passe" -ForegroundColor Red
    Write-Host "Restauration du backup..." -ForegroundColor Yellow
    Copy-Item $backupPath $pgHbaPath -Force
    Start-Service -Name $serviceName
    exit 1
}

# Étape 6 : Restaurer pg_hba.conf
Write-Host "[6/7] Restauration de pg_hba.conf (securite)..." -ForegroundColor Cyan
Copy-Item $backupPath $pgHbaPath -Force
Write-Host "[OK] pg_hba.conf restaure" -ForegroundColor Green

# Étape 7 : Redémarrer PostgreSQL
Write-Host "[7/7] Redemarrage final..." -ForegroundColor Cyan
Restart-Service -Name $serviceName -Force
Start-Sleep -Seconds 2
Write-Host "[OK] PostgreSQL redemarre" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUCCES!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Mot de passe PostgreSQL: $newPassword" -ForegroundColor White
Write-Host ""
Write-Host "Prochaines etapes:" -ForegroundColor Cyan
Write-Host "  cd C:\Users\abdoulaye.ousmane\decision-memory-v1" -ForegroundColor White
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python scripts\setup_db_with_password.py --password $newPassword" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
