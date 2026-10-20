#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
else
  . .venv/bin/activate
fi
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000