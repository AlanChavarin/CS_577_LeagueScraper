# PostgreSQL Database Restore Script
# Restores a backup into a local PostgreSQL instance using POSTGRES_* environment variables

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

# Get local connection details from environment
$POSTGRES_DB = $env:POSTGRES_DB
$POSTGRES_USER = $env:POSTGRES_USER
$POSTGRES_PASSWORD = $env:POSTGRES_PASSWORD
$POSTGRES_HOST = $env:POSTGRES_HOST
$POSTGRES_PORT = $env:POSTGRES_PORT

$missingVars = @()
if (-not $POSTGRES_DB) { $missingVars += "POSTGRES_DB" }
if (-not $POSTGRES_USER) { $missingVars += "POSTGRES_USER" }
if (-not $POSTGRES_PASSWORD) { $missingVars += "POSTGRES_PASSWORD" }
if (-not $POSTGRES_HOST) { $missingVars += "POSTGRES_HOST" }
if (-not $POSTGRES_PORT) { $missingVars += "POSTGRES_PORT" }

if ($missingVars.Count -gt 0) {
    Write-Host "Error: Missing required environment variables: $($missingVars -join ', ')" -ForegroundColor Red
    Write-Host "Please ensure these values are set in your .env file or environment variables." -ForegroundColor Yellow
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

$dbUser = $POSTGRES_USER
$dbHost = $POSTGRES_HOST
$dbPort = $POSTGRES_PORT
$dbName = $POSTGRES_DB
$dbPassword = $POSTGRES_PASSWORD

$psqlArgs = @(
    "-h", $dbHost,
    "-p", $dbPort,
    "-U", $dbUser,
    "-d", $dbName,
    "--echo-errors"
)

# Safety confirmation
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Yellow
Write-Host "WARNING: This will RESTORE data to LOCAL database!" -ForegroundColor Red
Write-Host ("=" * 60) -ForegroundColor Yellow
Write-Host ""
Write-Host "Backup file: $BackupFile" -ForegroundColor Cyan
Write-Host "Local database:" -ForegroundColor Cyan
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

    # Verify champions_roles is in backup before restoring
    Write-Host "Verifying backup file..." -ForegroundColor Cyan
    $backupContent = Get-Content $BackupFile -Raw
    if ($backupContent -match "champions_roles") {
        Write-Host "  [OK] champions_roles table found in backup" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] WARNING: champions_roles table NOT found in backup file!" -ForegroundColor Yellow
        Write-Host "  The restore will proceed, but champions_roles may not be restored." -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Restore SQL dump using psql with connection URI
    Write-Host "Restoring SQL dump..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes depending on database size..." -ForegroundColor Gray
    Write-Host ""
    
    # Use psql with the connection URI directly
    # Using --echo-errors to show any errors that occur
    # Redirect stderr to stdout to capture all output
    $restoreOutput = Get-Content $BackupFile | & psql @psqlArgs 2>&1 | Tee-Object -Variable restoreOutputVar
    
    # Check for errors in output (psql errors typically go to stderr)
    $errors = $restoreOutputVar | Where-Object { $_ -match "ERROR|FATAL|WARNING" }
    if ($errors) {
        Write-Host ""
        Write-Host "Errors/Warnings encountered during restore:" -ForegroundColor Yellow
        $errors | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[SUCCESS] Database restored successfully!" -ForegroundColor Green
        
        # Verify champions_roles table exists after restore
        Write-Host ""
        Write-Host "Verifying restore..." -ForegroundColor Cyan
        $verifyQuery = "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'champions_roles';"
        $verifyResult = & psql @psqlArgs "-t" "-A" "-c" $verifyQuery 2>&1
        if ($verifyResult -match '^\s*1\s*$') {
            Write-Host "  [OK] champions_roles table exists in database" -ForegroundColor Green
            
            # Check row count
            $countQuery = "SELECT COUNT(*) FROM champions_roles;"
            $rowCount = & psql @psqlArgs "-t" "-A" "-c" $countQuery 2>&1
            if ($rowCount -match '^\s*(\d+)\s*$') {
                $count = $matches[1]
                Write-Host "  [OK] champions_roles has $count rows" -ForegroundColor Green
            }
        } else {
            Write-Host "  [ERROR] WARNING: champions_roles table NOT found in database after restore!" -ForegroundColor Red
        }
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

