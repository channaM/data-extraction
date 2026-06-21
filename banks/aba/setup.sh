#!/bin/bash
# ABA Bank ETL Engine — macOS / Linux setup
# Run once to create the virtual environment and install dependencies.
# After this, always use:  venv/bin/python run.py <file>

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================"
echo "  ABA Bank ETL Engine — Setup"
echo "============================================"

# Check Python 3.10+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.10 or later."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PY_VER"

# Create venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Install dependencies
echo "Installing dependencies..."
venv/bin/pip install --upgrade pip --quiet
venv/bin/pip install -r requirements.txt --quiet

echo ""
echo "Setup complete."
echo ""
echo "To run the ETL engine:"
echo "  venv/bin/python run.py downloads/aba_sample_202501_USD.xlsx"
echo ""
