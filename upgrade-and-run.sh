#!/usr/bin/env bash
git fetch
git reset --hard origin/master --quiet
.venv/bin/python3 collect.py
