New-Item -ItemType Directory -Force -Path output

If (-not (Test-Path "COVID-19")) {
    git clone https://github.com/CSSEGISandData/COVID-19.git    
}

If (-not (Test-Path ".venv")) { py -3.7 -m venv .venv }
.venv\Scripts\activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
