# start.ps1 – inicia Backend FastAPI + Frontend Streamlit

# lê .env se existir
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.+)$") {
            [System.Environment]::SetEnvironmentVariable($matches<a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;">[1]</a>.Trim(), $matches<a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;">[2]</a>.Trim())
        }
    }
}

# BACKEND
$back = "uvicorn main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$PSScriptRoot`"; $back"

Start-Sleep 2  # espera backend subir

# FRONTEND
$front = "cd frontend; streamlit run app.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $front
