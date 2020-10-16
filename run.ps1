$ErrorActionPreference = "Stop"
function Invoke-Command {
    param ([scriptblock]$ScriptBlock)
    & @ScriptBlock
    if ($lastexitcode -ne 0) {
        Write-Host "ERROR happened, exiting..."
        exit $lastexitcode
    }
}

Write-Host "Update code repository"
Invoke-Command { git pull --ff-only }
Write-Host "Ensure dependencies"
Invoke-Command { .venv\Scripts\python -m pip install --upgrade pip }
Invoke-Command { .venv\Scripts\python -m pip install -r requirements.txt -q }

Write-Host "Update Datase from GitHub"
Invoke-Command { 
    Set-Location COVID-19
    git pull --ff-only
    Set-Location ..
}

Write-Host "Collect report"
Invoke-Command { .venv\Scripts\python collect.py }

Write-Host "Done"
