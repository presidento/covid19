#!/usr/bin/env bash
set -e
git fetch --quiet
git reset --hard origin/master --quiet

cd COVID-19
git pull --ff-only --quiet
cd ..

.venv/bin/python3 -m pip install -r requirements.txt --quiet
.venv/bin/python3 collect.py --quiet