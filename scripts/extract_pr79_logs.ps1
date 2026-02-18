# Script PowerShell pour extraire les logs de la PR #79
# Nécessite GitHub CLI (gh) installé

Write-Host "Extraction des logs CI pour PR #79..." -ForegroundColor Cyan

# Vérifier si gh est installé
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "ERREUR: GitHub CLI (gh) n'est pas installé." -ForegroundColor Red
    Write-Host "Installez-le depuis: https://cli.github.com/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Alternative: Utilisez le guide web dans docs/audits/PR79_QUICK_EXTRACTION_GUIDE.md" -ForegroundColor Yellow
    exit 1
}

# Vérifier l'authentification
Write-Host "Vérification de l'authentification GitHub..." -ForegroundColor Cyan
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Authentification requise. Exécutez: gh auth login" -ForegroundColor Yellow
    exit 1
}

# Créer le répertoire de sortie
$outputDir = "docs/audits/PR79_LOGS"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

Write-Host "Répertoire de sortie: $outputDir" -ForegroundColor Green

# Liste des run IDs identifiés
$runs = @(
    @{ID="22140169803"; Name="CI_MAIN"; Workflow="CI Main"},
    @{ID="22140169501"; Name="CI_INVARIANTS"; Workflow="CI Invariants"},
    @{ID="22140169500"; Name="MILESTONES_GATES"; Workflow="CI Milestones Gates"},
    @{ID="22140169486"; Name="CI_LINT_RUFF"; Workflow="CI Lint (Ruff)"},
    @{ID="22140169478"; Name="CI_FREEZE_INTEGRITY"; Workflow="CI Freeze Integrity"},
    @{ID="22140168216"; Name="REGENERATE_CHECKSUMS"; Workflow="Regenerate Freeze Checksums"},
    @{ID="22140155886"; Name="FORMAT_BLACK"; Workflow="Format Code with Black"}
)

Write-Host ""
Write-Host "Extraction des logs pour $($runs.Count) workflows..." -ForegroundColor Cyan
Write-Host ""

foreach ($run in $runs) {
    $outputFile = Join-Path $outputDir "PR79_LOGS_$($run.Name)_RUN_$($run.ID).txt"
    
    Write-Host "Extraction: $($run.Workflow) (Run $($run.ID))..." -ForegroundColor Yellow
    
    try {
        gh run view $run.ID --log | Out-File -FilePath $outputFile -Encoding UTF8
        if ($LASTEXITCODE -eq 0) {
            $fileSize = (Get-Item $outputFile).Length
            Write-Host "  ✓ Sauvegardé: $outputFile ($([math]::Round($fileSize/1KB, 2)) KB)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Échec extraction (code: $LASTEXITCODE)" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ Erreur: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Extraction terminée!" -ForegroundColor Green
Write-Host "Fichiers sauvegardés dans: $outputDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pour voir tous les runs disponibles:" -ForegroundColor Yellow
Write-Host "  gh run list --branch fix/audit-urgent --limit 20" -ForegroundColor White
