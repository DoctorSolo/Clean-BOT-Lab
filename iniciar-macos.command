#!/bin/bash
set -e
cd "$(dirname "$0")"
[ -f .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python -m app.launch
