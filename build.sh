#!/usr/bin/env bash
# Build a standalone `orch` executable for this platform with PyInstaller.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .build-venv
. .build-venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet . pyinstaller

pyinstaller src/orch_cli/__main__.py --onefile --name orch --paths src --clean

cp dist/orch .
deactivate
rm -rf .build-venv build dist ./*.spec
chmod +x orch
echo "Built ./orch"
