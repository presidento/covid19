python_dir := if os_family() == "windows" { "./.venv/Scripts" } else { "./.venv/bin" }
python := python_dir + if os_family() == "windows" { "/python.exe" } else { "/python3" }
system_python := if os_family() == "windows" { "py.exe -3.7" } else { "python3.7" }

# Set up development environment
bootstrap:
    if test ! -e .venv; then {{ system_python }} -m venv .venv --prompt covid19; fi
    {{ python }} -m pip install --upgrade pip wheel pip-tools
    {{ python }} -m piptools sync requirements.txt

    mkdir -p output
    if test ! -e COVID-19; then git clone https://github.com/CSSEGISandData/COVID-19.git; fi

# Upgrade Python dependencies
upgrade-deps: && bootstrap
    {{ python }} -m pip install pip pip-tools wheel --upgrade
    {{ python_dir }}/pip-compile --output-file=requirements.txt requirements.in --upgrade --annotation-style line

# Update data repository
update-data:
    git -C COVID-19 fetch
    git -C COVID-19 reset --hard origin/master

# Generate reports
generate *ARGS:
    {{ python }} collect.py {{ ARGS }}

clean:
    rm -rf output
    mkdir output

# Run everything from scratch to full build
run: bootstrap update-data generate
