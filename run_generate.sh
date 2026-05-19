#!/usr/bin/env bash
# Python 3.14 on Homebrew often breaks venv/pip (ensurepip). Use 3.13 instead.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3.13}"
if ! command -v "$PY" &>/dev/null; then
  echo "Need python3.13. Install: brew install python@3.13"
  exit 1
fi

VENV=".venv313"
if [[ ! -d "$VENV" ]]; then
  "$PY" -m venv "$VENV"
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"
pip install -q -r requirements.txt
python generate_thy_designs.py
echo "OK — images/thy-design-a.png and thy-design-b.png"
