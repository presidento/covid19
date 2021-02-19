#!/usr/bin/env bash
set -e
git fetch --quiet >/dev/null 2>/dev/null
git reset --hard origin/master --quiet

cd COVID-19
git pull --ff-only --quiet >/dev/null 2>/dev/null
cd ..

rm -rf output/
.venv/bin/python3 -m pip install pip --upgrade --quiet
.venv/bin/python3 -m pip install -r requirements.txt --quiet
.venv/bin/python3 collect.py --quiet