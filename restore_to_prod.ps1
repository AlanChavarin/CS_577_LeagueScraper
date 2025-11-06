# PostgreSQL Database Restore Script
# Restores a local backup to production database using DATABASE_PUBLIC_URL

param(
    [string]$BackupFile = ""
)

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

# Get DATABASE_PUBLIC_URL from environment
$DATABASE_PUBLIC_URL = $env:DATABASE_PUBLIC_URL

if (-not $DATABASE_PUBLIC_URL) {
    Write-Host "Error: DATABASE_PUBLIC_URL not found in .env file or environment variables." -ForegroundColor Red
    Write-Host "Please ensure DATABASE_PUBLIC_URL is set in your .env file." -ForegroundColor Yellow
    exit 1
}

# Check backups directory
$backupDir = "backups"
if (-not (Test-Path $backupDir)) {
    Write-Host "Error: Backups directory not found: $backupDir" -ForegroundColor Red
    exit 1
}

# If no backup file specified, list available backups and prompt user
if (-not $BackupFile) {
    $backupFiles = Get-ChildItem -Path $backupDir -Filter "league_db_backup_*.sql" | Sort-Object LastWriteTime -Descending
    
    if ($backupFiles.Count -eq 0) {
        Write-Host "Error: No backup files found in $backupDir" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Available backup files:" -ForegroundColor Cyan
    Write-Host ""
    for ($i = 0; $i -lt $backupFiles.Count; $i++) {
        $file = $backupFiles[$i]
        $fileSize = [math]::Round($file.Length / 1MB, 2)
        $date = $file.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        Write-Host "  [$i] $($file.Name)" -ForegroundColor White
        Write-Host "      Size: $fileSize MB | Date: $date" -ForegroundColor Gray
    }
    Write-Host ""
    
    $selection = Read-Host "Enter the number of the backup to restore (or press Enter for latest)"
    
    if ($selection -eq "") {
        $BackupFile = $backupFiles[0].FullName
        Write-Host "Selected latest backup: $($backupFiles[0].Name)" -ForegroundColor Green
    } elseif ($selection -match '^\d+$' -and [int]$selection -ge 0 -and [int]$selection -lt $backupFiles.Count) {
        $BackupFile = $backupFiles[[int]$selection].FullName
        Write-Host "Selected: $($backupFiles[[int]$selection].Name)" -ForegroundColor Green
    } else {
        Write-Host "Error: Invalid selection." -ForegroundColor Red
        exit 1
    }
} else {
    # Backup file specified as parameter
    if (-not (Test-Path $BackupFile)) {
        # Try relative to backups directory
        $BackupFile = Join-Path $backupDir $BackupFile
        if (-not (Test-Path $BackupFile)) {
            Write-Host "Error: Backup file not found: $BackupFile" -ForegroundColor Red
            exit 1
        }
    }
    $BackupFile = (Resolve-Path $BackupFile).Path
}

# Verify backup file exists
if (-not (Test-Path $BackupFile)) {
    Write-Host "Error: Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

# Parse DATABASE_PUBLIC_URL to extract connection info for display
# Format: postgresql://user:password@host:port/database
$urlPattern = 'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
if ($DATABASE_PUBLIC_URL -match $urlPattern) {
    $dbUser = $matches[1]
    $dbHost = $matches[3]
    $dbPort = $matches[4]
    $dbName = $matches[5]
    $dbPassword = $matches[2]
} else {
    Write-Host "Warning: Could not parse DATABASE_PUBLIC_URL format. Proceeding anyway..." -ForegroundColor Yellow
    $dbUser = "unknown"
    $dbHost = "unknown"
    $dbPort = "unknown"
    $dbName = "unknown"
}

# Safety confirmation
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Yellow
Write-Host "WARNING: This will RESTORE data to PRODUCTION database!" -ForegroundColor Red
Write-Host ("=" * 60) -ForegroundColor Yellow
Write-Host ""
Write-Host "Backup file: $BackupFile" -ForegroundColor Cyan
Write-Host "Production database:" -ForegroundColor Cyan
Write-Host "  Host: $dbHost" -ForegroundColor Gray
Write-Host "  Port: $dbPort" -ForegroundColor Gray
Write-Host "  Database: $dbName" -ForegroundColor Gray
Write-Host "  User: $dbUser" -ForegroundColor Gray
Write-Host ""

$confirm = Read-Host "Type 'YES' to confirm restore to production database"
if ($confirm -ne "YES") {
    Write-Host "Restore cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Starting database restore..." -ForegroundColor Cyan

try {
    # Check if psql is available
    $psqlPath = Get-Command psql -ErrorAction SilentlyContinue
    if (-not $psqlPath) {
        throw "psql not found. Please ensure PostgreSQL client tools are installed and in your PATH."
    }

    # Set PGPASSWORD environment variable for psql (avoids password prompt)
    if ($dbPassword) {
        $env:PGPASSWORD = $dbPassword
    }

    # Restore SQL dump using psql with connection URI
    Write-Host "Restoring SQL dump..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes depending on database size..." -ForegroundColor Gray
    Write-Host ""
    
    # Use psql with the connection URI directly
    Get-Content $BackupFile | & psql $DATABASE_PUBLIC_URL
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[SUCCESS] Database restored successfully!" -ForegroundColor Green
    } else {
        throw "psql failed with exit code $LASTEXITCODE"
    }

} catch {
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
} finally {
    # Clear password from environment
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

