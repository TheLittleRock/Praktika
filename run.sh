#!/bin/bash
set -e

# Change to the script's directory
cd "$(dirname "$0")"

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

echo "Starting Praktika Evaluation Studio on http://localhost:8000..."
./venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

