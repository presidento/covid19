set shell := ["powershell", "-nop", "-c"]

python_dir := justfile_directory() + "\\.venv\\Scripts"
python := python_dir + "\\python.exe"

# Set up development environment
bootstrap:
    If (-not (Test-Path ".venv")) { py -3.7 -m venv .venv --prompt covid19 }
    {{ python }} -m pip install --upgrade pip wheel pip-tools
    {{ python }} -m piptools sync requirements.txt

    New-Item -ItemType Directory -Force -Path output
    If (-not (Test-Path "COVID-19")) { git clone https://github.com/CSSEGISandData/COVID-19.git }

# Upgrade Python dependencies
upgrade-deps: && bootstrap
    {{ python }} -m pip install pip pip-tools wheel --upgrade
    {{ python_dir }}\pip-compile --output-file=requirements.txt requirements.in --upgrade --annotation-style line

# Update data repository
update-data:
    git -C COVID-19 pull --ff-only

# Generate reports
generate *ARGS:
    {{ python }} collect.py {{ ARGS }}

run: bootstrap update-data generate
