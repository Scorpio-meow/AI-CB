# Log Analysis Tool for ChatBot Backend
# PowerShell script to analyze application logs

param(
    [string]$LogFile = "logs/app.log",
    [string]$Action = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host "  Log Analysis Tool" -ForegroundColor Cyan  
    Write-Host "=====================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\analyze_logs.ps1 -Action <action>" -ForegroundColor White
    Write-Host ""
    Write-Host "Available Actions:" -ForegroundColor Yellow
    Write-Host "  cache-hit      - Show cache hit count" -ForegroundColor Green
    Write-Host "  cache-miss     - Show cache miss count" -ForegroundColor Green
    Write-Host "  cache-stats    - Show cache statistics" -ForegroundColor Green
    Write-Host "  errors         - Show error logs" -ForegroundColor Green
    Write-Host "  recent         - Show recent 50 log lines" -ForegroundColor Green
    Write-Host "  sql            - Show SQL query logs" -ForegroundColor Green
    Write-Host "  performance    - Show performance logs" -ForegroundColor Green
    Write-Host "  help           - Show this help message" -ForegroundColor Green
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\analyze_logs.ps1 -Action cache-stats"
    Write-Host "  .\analyze_logs.ps1 -Action errors"
    Write-Host ""
}

function Get-CacheHitCount {
    $hits = Select-String -Path $LogFile -Pattern "Cache hit" -ErrorAction SilentlyContinue
    $count = if ($hits) { $hits.Count } else { 0 }
    Write-Host "Cache Hits: $count" -ForegroundColor Green
    return $count
}

function Get-CacheMissCount {
    $misses = Select-String -Path $LogFile -Pattern "Cache miss" -ErrorAction SilentlyContinue
    $count = if ($misses) { $misses.Count } else { 0 }
    Write-Host "Cache Misses: $count" -ForegroundColor Yellow
    return $count
}

function Show-CacheStats {
    Write-Host ""
    Write-Host "Cache Statistics Analysis" -ForegroundColor Cyan
    Write-Host "=" * 60
    
    $hits = Get-CacheHitCount
    $misses = Get-CacheMissCount
    $total = $hits + $misses
    
    if ($total -gt 0) {
        $hitRate = [math]::Round(($hits / $total) * 100, 2)
        Write-Host ""
        Write-Host "Total Requests: $total" -ForegroundColor White
        Write-Host "Cache Hit Rate: $hitRate%" -ForegroundColor $(if ($hitRate -gt 60) { "Green" } elseif ($hitRate -gt 40) { "Yellow" } else { "Red" })
        
        if ($hitRate -gt 60) {
            Write-Host "Status: Excellent cache performance!" -ForegroundColor Green
        } elseif ($hitRate -gt 40) {
            Write-Host "Status: Average cache performance, consider adjusting TTL" -ForegroundColor Yellow
        } else {
            Write-Host "Status: Poor cache performance, optimization needed" -ForegroundColor Red
        }
    } else {
        Write-Host ""
        Write-Host "Warning: No cache records found" -ForegroundColor Yellow
        Write-Host "Possible reasons:" -ForegroundColor Gray
        Write-Host "  1. Cache not enabled (CACHE_ENABLED=false)" -ForegroundColor Gray
        Write-Host "  2. No API requests yet" -ForegroundColor Gray
        Write-Host "  3. Log level set to WARNING or higher" -ForegroundColor Gray
    }
    Write-Host ""
}

function Show-Errors {
    Write-Host ""
    Write-Host "Error Logs (Last 20)" -ForegroundColor Red
    Write-Host "=" * 60
    
    $errors = Select-String -Path $LogFile -Pattern "ERROR|Exception|Traceback" -Context 0,2 -ErrorAction SilentlyContinue | Select-Object -Last 20
    
    if ($errors) {
        $errors | ForEach-Object {
            Write-Host $_.Line -ForegroundColor Red
            if ($_.Context.PostContext) {
                $_.Context.PostContext | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
            }
            Write-Host ""
        }
    } else {
        Write-Host "OK: No errors found" -ForegroundColor Green
    }
}

function Show-RecentLogs {
    Write-Host ""
    Write-Host "Recent Logs (50 lines)" -ForegroundColor Cyan
    Write-Host "=" * 60
    
    Get-Content $LogFile -Tail 50 -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_ -match "ERROR") {
            Write-Host $_ -ForegroundColor Red
        } elseif ($_ -match "WARNING") {
            Write-Host $_ -ForegroundColor Yellow
        } elseif ($_ -match "Cache hit") {
            Write-Host $_ -ForegroundColor Green
        } else {
            Write-Host $_
        }
    }
}

function Show-SQLQueries {
    Write-Host ""
    Write-Host "SQL Query Logs (Last 20)" -ForegroundColor Cyan
    Write-Host "=" * 60
    
    $queries = Select-String -Path $LogFile -Pattern "SELECT|INSERT|UPDATE|DELETE|BEGIN|COMMIT" -ErrorAction SilentlyContinue | Select-Object -Last 20
    
    if ($queries) {
        $queries | ForEach-Object {
            Write-Host $_.Line -ForegroundColor Cyan
        }
        Write-Host ""
        Write-Host "Warning: If you see many SQL logs, check SQLALCHEMY_ECHO setting" -ForegroundColor Yellow
    } else {
        Write-Host "OK: SQL logging is disabled (recommended for production)" -ForegroundColor Green
    }
}

function Show-Performance {
    Write-Host ""
    Write-Host "Performance Logs" -ForegroundColor Cyan
    Write-Host "=" * 60
    
    Write-Host ""
    Write-Host "[API Response Times]" -ForegroundColor White
    $timeouts = Select-String -Path $LogFile -Pattern "timeout|took|elapsed" -ErrorAction SilentlyContinue | Select-Object -Last 10
    if ($timeouts) {
        $timeouts | ForEach-Object { Write-Host $_.Line }
    } else {
        Write-Host "No response time records found" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "[Database Connection Pool]" -ForegroundColor White
    $pool = Select-String -Path $LogFile -Pattern "pool|connection" -ErrorAction SilentlyContinue | Select-Object -Last 5
    if ($pool) {
        $pool | ForEach-Object { Write-Host $_.Line }
    } else {
        Write-Host "No connection pool records found" -ForegroundColor Gray
    }
}

# Main Logic
if (-not (Test-Path $LogFile)) {
    Write-Host "Error: Log file not found: $LogFile" -ForegroundColor Red
    Write-Host "Please run this script from the backend directory" -ForegroundColor Yellow
    exit 1
}

switch ($Action.ToLower()) {
    "cache-hit" { Get-CacheHitCount }
    "cache-miss" { Get-CacheMissCount }
    "cache-stats" { Show-CacheStats }
    "errors" { Show-Errors }
    "recent" { Show-RecentLogs }
    "sql" { Show-SQLQueries }
    "performance" { Show-Performance }
    "help" { Show-Help }
    default { 
        Write-Host "Unknown action: $Action" -ForegroundColor Red
        Show-Help 
    }
}
