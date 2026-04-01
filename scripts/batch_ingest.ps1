# DMS — Batch Ingest : OCR + push vers Label Studio
# Usage :
#   .\scripts\batch_ingest.ps1 -SourceRoot "C:\path\to\pdfs"
#   .\scripts\batch_ingest.ps1 -SourceRoot "C:\path\to\pdfs" -OutputRoot "data\ingest\batch_output"

param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot,

    [string]$OutputRoot = "data\ingest\batch_output",

    [switch]$CloudFirst,

    [switch]$SkipLsPush
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

Write-Host "=============================================="
Write-Host "  DMS Batch Ingest Pipeline"
Write-Host "=============================================="
Write-Host "  Source  : $SourceRoot"
Write-Host "  Output  : $OutputRoot"
Write-Host "  Cloud   : $($CloudFirst.IsPresent)"
Write-Host "  Start   : $startTime"
Write-Host ""

# Verifier que le dossier source existe
if (-not (Test-Path $SourceRoot)) {
    Write-Error "Dossier source introuvable : $SourceRoot"
    exit 1
}

# Compter les PDFs
$pdfCount = (Get-ChildItem -Path $SourceRoot -Filter "*.pdf" -Recurse | Measure-Object).Count
Write-Host "  PDFs detectes : $pdfCount"

if ($pdfCount -eq 0) {
    Write-Warning "Aucun PDF trouve dans $SourceRoot"
    exit 0
}

# Creer le dossier de sortie
if (-not (Test-Path $OutputRoot)) {
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

# Lancer le bridge
Write-Host ""
Write-Host ":: Lancement du bridge OCR..."
$bridgeArgs = @(
    "scripts/ingest_to_annotation_bridge.py",
    "--source-root", $SourceRoot,
    "--output-root", $OutputRoot
)

if ($CloudFirst.IsPresent) {
    $bridgeArgs += "--cloud-first"
}

python @bridgeArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Bridge OCR echoue (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

# Verifier le rapport
$reportPath = Join-Path $OutputRoot "ingest_report.json"
if (Test-Path $reportPath) {
    Write-Host ""
    Write-Host ":: Rapport d'ingestion :"
    $report = Get-Content $reportPath -Raw | ConvertFrom-Json
    Write-Host "  Total      : $($report.total_files)"
    Write-Host "  OCR OK     : $($report.ocr_success)"
    Write-Host "  OCR Failed : $($report.ocr_failed)"
    Write-Host "  Skipped    : $($report.skipped)"
}

# Push vers Label Studio (sauf si --SkipLsPush)
$lsTasksPath = Join-Path $OutputRoot "ls_tasks.json"
if (-not $SkipLsPush.IsPresent -and (Test-Path $lsTasksPath)) {
    Write-Host ""
    Write-Host ":: Push vers Label Studio..."

    $lsUrl = $env:LABEL_STUDIO_URL
    $lsKey = $env:LABEL_STUDIO_API_KEY
    $lsProject = if ($env:LABEL_STUDIO_PROJECT_ID) { $env:LABEL_STUDIO_PROJECT_ID } else { "1" }

    if ($lsUrl -and $lsKey) {
        $tasks = Get-Content $lsTasksPath -Raw
        $headers = @{
            "Authorization" = "Token $lsKey"
            "Content-Type" = "application/json"
        }
        try {
            $response = Invoke-RestMethod `
                -Uri "$($lsUrl.TrimEnd('/'))/api/projects/$lsProject/import" `
                -Method Post `
                -Headers $headers `
                -Body $tasks `
                -TimeoutSec 60

            Write-Host "  Label Studio import OK : $($response.task_count) tasks"
        } catch {
            Write-Warning "Push Label Studio echoue : $_"
        }
    } else {
        Write-Host "  LABEL_STUDIO_URL ou LABEL_STUDIO_API_KEY non definis — push skipped"
    }
}

$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host ""
Write-Host ":: Termine en $($duration.TotalSeconds.ToString('F1'))s"
Write-Host ":: Sortie dans : $OutputRoot"
