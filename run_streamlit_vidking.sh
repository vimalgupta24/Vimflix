#!/bin/bash
# Vimflix - Streamlit frontend (Python only). Vidking: https://www.vidking.net/documentation
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 &> /dev/null; then
  echo "Python 3 is required."
  exit 1
fi

if [ ! -d "$SCRIPT_DIR/venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$SCRIPT_DIR/venv"
fi

VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
if [ ! -f "$REQUIREMENTS" ]; then
  echo "ERROR: requirements.txt not found at $REQUIREMENTS"
  exit 1
fi
"$VENV_PYTHON" -m pip install -q -r "$REQUIREMENTS"

echo "Starting Vimflix (Streamlit) at http://localhost:8501"
if command -v open &> /dev/null; then
  (sleep 2 && open "http://localhost:8501") &
elif command -v xdg-open &> /dev/null; then
  (sleep 2 && xdg-open "http://localhost:8501") &
fi

exec "$VENV_PYTHON" -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
