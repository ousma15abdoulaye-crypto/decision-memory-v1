# DMS Local PostgreSQL Setup Script
# Creates database 'dms' and role 'dms' with pg_trgm extension

param(
    [string]$PostgresUser = "postgres",
    [string]$PostgresPassword = "",
    [string]$DbName = "dms",
    [string]$DbUser = "dms",
    [string]$DbPassword = "dms_dev_password_change_me"
)

$psqlPath = "C:\Program Files\PostgreSQL\15\bin\psql.exe"

if (-not (Test-Path $psqlPath)) {
    Write-Host "ERROR: psql.exe not found at $psqlPath" -ForegroundColor Red
    Write-Host "Please adjust the path in this script or add PostgreSQL bin to PATH" -ForegroundColor Yellow
    exit 1
}

if ([string]::IsNullOrEmpty($PostgresPassword)) {
    Write-Host "PostgreSQL superuser password required." -ForegroundColor Yellow
    $securePassword = Read-Host "Enter password for user '$PostgresUser'" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $PostgresPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

$env:PGPASSWORD = $PostgresPassword

Write-Host "Creating role '$DbUser'..." -ForegroundColor Cyan
& $psqlPath -h localhost -p 5432 -U $PostgresUser -d postgres -c @"
DO `$`$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$DbUser') THEN
    CREATE ROLE $DbUser LOGIN PASSWORD '$DbPassword';
  ELSE
    ALTER ROLE $DbUser PASSWORD '$DbPassword';
  END IF;
END`$`$;
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create role" -ForegroundColor Red
    exit 1
}

Write-Host "Creating database '$DbName'..." -ForegroundColor Cyan
& $psqlPath -h localhost -p 5432 -U $PostgresUser -d postgres -c "CREATE DATABASE $DbName OWNER $DbUser;" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Database might already exist, continuing..." -ForegroundColor Yellow
}

Write-Host "Enabling pg_trgm extension..." -ForegroundColor Cyan
$env:PGPASSWORD = $DbPassword
& $psqlPath -h localhost -p 5432 -U $DbUser -d $DbName -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Setup complete!" -ForegroundColor Green
    Write-Host "Database: $DbName" -ForegroundColor Green
    Write-Host "User: $DbUser" -ForegroundColor Green
    Write-Host "Password: $DbPassword" -ForegroundColor Green
    Write-Host "`nAdd to .env file:" -ForegroundColor Cyan
    Write-Host "DATABASE_URL=postgresql+psycopg://${DbUser}:${DbPassword}@localhost:5432/${DbName}" -ForegroundColor White
} else {
    Write-Host "ERROR: Failed to enable pg_trgm extension" -ForegroundColor Red
    exit 1
}

$env:PGPASSWORD = ""
