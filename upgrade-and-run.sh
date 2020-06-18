#!/usr/bin/env bash
set -e
git fetch
git reset --hard origin/master --quiet
.venv/bin/python3 -m pip install -r requirements.txt
.venv/bin/python3 collect.py
