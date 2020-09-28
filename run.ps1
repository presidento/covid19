$ErrorActionPreference = "Stop"
function Run-Command {
    param ([scriptblock]$ScriptBlock)
    & @ScriptBlock
    if ($lastexitcode -ne 0) {
        write-host "ERROR happened, exiting..."
        exit $lastexitcode
    }
}

write-host "Update code repository"
Run-Command { git pull --ff-only }
Run-Command { .venv\Scripts\python -m pip install -r requirements.txt -q }

write-host "Update Datase from GitHub"
Run-Command { 
    cd COVID-19
    git pull --ff-only
    cd ..
}

write-host "Collect report"
Run-Command { .venv\Scripts\python collect.py }

write-host "Done"
