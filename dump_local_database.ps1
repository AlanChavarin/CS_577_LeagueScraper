# PostgreSQL Database Backup Script
# Uses credentials from backend/config/settings.py

# Load .env file if it exists (similar to Django's load_dotenv())
$envFile = ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)\s*$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes if present
            if ($value -match '^["''](.*)["'']$') {
                $value = $matches[1]
            }
            # Only set if not already in environment (env vars take precedence)
            if (-not (Test-Path "Env:\$key")) {
                Set-Item -Path "Env:\$key" -Value $value
            }
        }
    }
}

# Get environment variables or use defaults (matching settings.py)
$POSTGRES_DB = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "postgres" }
$POSTGRES_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$POSTGRES_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "postgres" }
$POSTGRES_HOST = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$POSTGRES_PORT = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5433" }

# Create backups directory if it doesn't exist
$backupDir = "backups"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
    Write-Host "Created backups directory: $backupDir" -ForegroundColor Green
}

# Generate timestamp for backup filename
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupFile = "$backupDir\league_db_backup_$timestamp.sql"

# Set PGPASSWORD environment variable for pg_dump (avoids password prompt)
$env:PGPASSWORD = $POSTGRES_PASSWORD

Write-Host "Starting database backup..." -ForegroundColor Cyan
Write-Host "Database: $POSTGRES_DB" -ForegroundColor Gray
Write-Host "Host: $POSTGRES_HOST" -ForegroundColor Gray
Write-Host "Port: $POSTGRES_PORT" -ForegroundColor Gray
Write-Host ""

try {
    # Check if pg_dump is available
    $pgDumpPath = Get-Command pg_dump -ErrorAction SilentlyContinue
    if (-not $pgDumpPath) {
        throw "pg_dump not found. Please ensure PostgreSQL client tools are installed and in your PATH."
    }

    # Create SQL dump (plain text format)
    Write-Host "Creating SQL dump..." -ForegroundColor Yellow
    & pg_dump -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -F p -f $backupFile
    
    if ($LASTEXITCODE -eq 0) {
        $fileSize = (Get-Item $backupFile).Length / 1MB
        Write-Host "[SUCCESS] Backup created successfully: $backupFile" -ForegroundColor Green
        Write-Host "  File size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
    } else {
        throw "pg_dump failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "Backup completed successfully!" -ForegroundColor Green
    Write-Host "Backup location: $((Get-Location).Path)\$backupDir" -ForegroundColor Gray

} catch {
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
} finally {
    # Clear password from environment
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

