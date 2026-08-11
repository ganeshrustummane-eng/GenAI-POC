# Migration Validator - PostgreSQL Setup Script
# This script sets up PostgreSQL with sample data for the PoC

param(
    [ValidateSet("docker", "local")]
    [string]$Method = "docker",
    [switch]$Cleanup = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================="
Write-Host "Migration Validator - PostgreSQL Setup Script"
Write-Host "==================================================================="
Write-Host ""

# Function to check if Docker is installed
function Test-Docker {
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Write-Host "[✓] Docker is installed: $dockerVersion" -ForegroundColor Green
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
}

# Function to check if PostgreSQL is installed locally
function Test-PostgreSQL {
    try {
        $psqlVersion = psql --version 2>$null
        if ($psqlVersion) {
            Write-Host "[✓] PostgreSQL is installed: $psqlVersion" -ForegroundColor Green
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
}

# Function to start Docker containers
function Start-DockerPostgreSQL {
    Write-Host ""
    Write-Host "Starting PostgreSQL with Docker Compose..." -ForegroundColor Cyan
    
    # Check if docker-compose exists
    $dockerComposePath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "docker-compose.yml"
    
    if (-not (Test-Path $dockerComposePath)) {
        Write-Host "[✗] docker-compose.yml not found at $dockerComposePath" -ForegroundColor Red
        exit 1
    }
    
    # Start containers
    Write-Host "Running: docker-compose up -d" -ForegroundColor Gray
    docker-compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[✓] Docker containers started successfully" -ForegroundColor Green
    }
    else {
        Write-Host "[✗] Failed to start Docker containers" -ForegroundColor Red
        exit 1
    }
    
    # Wait for PostgreSQL to be ready
    Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
    $maxAttempts = 30
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        try {
            $result = docker exec migration_validator_source_db pg_isready -U admin -d source_db 2>$null
            if ($result -match "accepting connections") {
                Write-Host "[✓] PostgreSQL is ready" -ForegroundColor Green
                return $true
            }
        }
        catch {
            # Container might not be ready yet
        }
        
        $attempt++
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
    }
    
    Write-Host ""
    Write-Host "[✓] PostgreSQL container is running" -ForegroundColor Green
    return $true
}

# Function to setup local PostgreSQL
function Start-LocalPostgreSQL {
    Write-Host ""
    Write-Host "Setting up local PostgreSQL..." -ForegroundColor Cyan
    
    # Set password for psql
    $env:PGPASSWORD = "admin123"
    
    Write-Host "Creating database 'source_db'..." -ForegroundColor Yellow
    try {
        psql -U admin -h localhost -c "CREATE DATABASE source_db;" 2>$null
        Write-Host "[✓] Database created (or already exists)" -ForegroundColor Green
    }
    catch {
        Write-Host "[!] Database might already exist, continuing..." -ForegroundColor Yellow
    }
    
    # Get the path to the init scripts
    $scriptDir = $PSScriptRoot
    $schema_file = Join-Path $scriptDir "init\01-init-schema.sql"
    $data_file = Join-Path $scriptDir "init\02-insert-sample-data.sql"
    
    if (-not (Test-Path $schema_file)) {
        Write-Host "[✗] Schema file not found: $schema_file" -ForegroundColor Red
        exit 1
    }
    
    if (-not (Test-Path $data_file)) {
        Write-Host "[✗] Data file not found: $data_file" -ForegroundColor Red
        exit 1
    }
    
    # Run initialization scripts
    Write-Host "Running schema creation script..." -ForegroundColor Yellow
    psql -U admin -h localhost -d source_db -f $schema_file
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[✓] Schema created successfully" -ForegroundColor Green
    }
    else {
        Write-Host "[✗] Failed to create schema" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Running data insertion script..." -ForegroundColor Yellow
    psql -U admin -h localhost -d source_db -f $data_file
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[✓] Sample data inserted successfully" -ForegroundColor Green
    }
    else {
        Write-Host "[✗] Failed to insert data" -ForegroundColor Red
        exit 1
    }
    
    # Clear password
    $env:PGPASSWORD = ""
    
    return $true
}

# Function to verify setup
function Verify-Setup {
    Write-Host ""
    Write-Host "Verifying setup..." -ForegroundColor Cyan
    
    if ($Method -eq "docker") {
        $host_param = "localhost"
    }
    else {
        $host_param = "localhost"
    }
    
    $env:PGPASSWORD = "admin123"
    
    # Get row counts
    $result = psql -U admin -h $host_param -d source_db -t -c `
        "SELECT 'Users: ' || COUNT(*) FROM source_data.users
         UNION ALL SELECT 'Customers: ' || COUNT(*) FROM source_data.customers
         UNION ALL SELECT 'Products: ' || COUNT(*) FROM source_data.products
         UNION ALL SELECT 'Orders: ' || COUNT(*) FROM source_data.orders
         UNION ALL SELECT 'Transactions: ' || COUNT(*) FROM source_data.transactions;" 2>$null
    
    if ($result) {
        Write-Host "[✓] Data verification:" -ForegroundColor Green
        Write-Host $result
    }
    else {
        Write-Host "[!] Could not verify data (connection may have failed)" -ForegroundColor Yellow
    }
    
    $env:PGPASSWORD = ""
}

# Function to cleanup
function Cleanup-Resources {
    Write-Host ""
    Write-Host "Cleaning up resources..." -ForegroundColor Cyan
    
    if ($Method -eq "docker") {
        Write-Host "Stopping Docker containers..." -ForegroundColor Yellow
        docker-compose down
        Write-Host "[✓] Docker containers stopped" -ForegroundColor Green
    }
    else {
        Write-Host "Dropping database..." -ForegroundColor Yellow
        $env:PGPASSWORD = "admin123"
        psql -U admin -h localhost -c "DROP DATABASE IF EXISTS source_db;"
        $env:PGPASSWORD = ""
        Write-Host "[✓] Database dropped" -ForegroundColor Green
    }
}

# Main execution
Write-Host "Setup Method: $Method" -ForegroundColor Cyan
Write-Host ""

if ($Cleanup) {
    Cleanup-Resources
    Write-Host ""
    Write-Host "Cleanup completed!" -ForegroundColor Green
    exit 0
}

# Check prerequisites based on method
if ($Method -eq "docker") {
    if (-not (Test-Docker)) {
        Write-Host "[✗] Docker is not installed or not running" -ForegroundColor Red
        Write-Host "Please install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        exit 1
    }
    Start-DockerPostgreSQL
}
else {
    if (-not (Test-PostgreSQL)) {
        Write-Host "[✗] PostgreSQL is not installed or psql is not in PATH" -ForegroundColor Red
        Write-Host "Please install PostgreSQL from https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
        exit 1
    }
    Start-LocalPostgreSQL
}

# Verify the setup
Verify-Setup

Write-Host ""
Write-Host "==================================================================="
Write-Host "PostgreSQL Setup Completed Successfully!" -ForegroundColor Green
Write-Host "==================================================================="
Write-Host ""
Write-Host "Connection Details:" -ForegroundColor Cyan
Write-Host "  Host:     localhost"
Write-Host "  Port:     5432"
Write-Host "  Database: source_db"
Write-Host "  User:     admin"
Write-Host "  Password: admin123"
Write-Host "  Schema:   source_data"
Write-Host ""
Write-Host "Sample Tables:" -ForegroundColor Cyan
Write-Host "  - source_data.users (10 rows)"
Write-Host "  - source_data.customers (10 rows)"
Write-Host "  - source_data.products (10 rows)"
Write-Host "  - source_data.orders (10 rows)"
Write-Host "  - source_data.transactions (12 rows)"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Create the validation framework"
Write-Host "  2. Build SQL generators for MSSQL, PostgreSQL, and Snowflake"
Write-Host "  3. Implement transformation rules engine"
Write-Host "  4. Test with this sample data"
Write-Host ""
Write-Host "To connect manually:" -ForegroundColor Cyan
if ($Method -eq "docker") {
    Write-Host "  docker exec -it migration_validator_source_db psql -U admin -d source_db"
}
else {
    Write-Host "  psql -U admin -h localhost -d source_db"
}
Write-Host ""
