$ErrorActionPreference = "Stop"

$requiredVars = @(
    "DATABASE_URL",
    "MISTRAL_API_KEY",
    "REDIS_URL",
    "WORKER_AUTH_TOKEN",
    "JWT_SECRET",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET",
    "R2_ENDPOINT",
    "LABEL_STUDIO_API_KEY"
)

$missing = @()

foreach ($name in $requiredVars) {
    $value = [Environment]::GetEnvironmentVariable($name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "[DMS ENV] $name MISSING"
        $missing += $name
    } else {
        Write-Host "[DMS ENV] $name OK"
    }
}

if ($missing.Count -gt 0) {
    Write-Host "[DMS ENV] Missing required variables: $($missing.Count)"
    exit 1
}

Write-Host "[DMS ENV] All required variables present"
exit 0
