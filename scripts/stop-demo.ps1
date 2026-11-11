# Stop listeners on ports 8000 (uvicorn) and 3000 (Next.js) gently.
# Usage: .\scripts\stop-demo.ps1

$ports = @(8000, 3000)
$killed = @()

foreach ($port in $ports) {
    $pids = @()
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($conns) {
            $pids = @($conns | Select-Object -ExpandProperty OwningProcess -Unique)
        }
    } catch {
        # Fallback via netstat when Get-NetTCPConnection is unavailable
    }

    if (-not $pids -or $pids.Count -eq 0) {
        $lines = netstat -ano | Select-String -Pattern ":$port\s+.*LISTENING"
        foreach ($line in $lines) {
            $parts = ($line.ToString() -split "\s+") | Where-Object { $_ -ne "" }
            if ($parts.Count -ge 5) {
                $pids += [int]$parts[-1]
            }
        }
        $pids = @($pids | Select-Object -Unique)
    }

    foreach ($procId in $pids) {
        if (-not $procId -or $procId -eq 0) { continue }
        try {
            $proc = Get-Process -Id $procId -ErrorAction Stop
            Write-Host "Stopping PID $procId ($($proc.ProcessName)) on port $port"
            Stop-Process -Id $procId -ErrorAction Stop
            $killed += $procId
        } catch {
            Write-Host "Could not stop PID $procId on port $port : $($_.Exception.Message)"
        }
    }

    if (-not $pids -or $pids.Count -eq 0) {
        Write-Host "No listener on port $port"
    }
}

if ($killed.Count -gt 0) {
    Write-Host "Stopped PIDs: $($killed -join ', ')"
} else {
    Write-Host "Nothing to stop."
}
