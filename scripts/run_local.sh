#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d .venv ]]; then
  python -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

export FB_VERIFY_TOKEN="${FB_VERIFY_TOKEN:-dev-verify-token}"
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
