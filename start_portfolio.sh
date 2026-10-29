#!/usr/bin/env bash
# WSG Innovation Portfolio — start on macOS / Linux (needs Python 3.11+)
set -e
cd "$(dirname "$0")/backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
echo "Open http://127.0.0.1:8001  — data in backend/portfolio.db, backups in backend/backups/"
.venv/bin/python -m uvicorn app.main:app --port 8001
