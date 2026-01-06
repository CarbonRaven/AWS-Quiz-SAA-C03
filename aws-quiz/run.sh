#!/bin/bash
# AWS Quiz Runner

cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install flask
else
    source venv/bin/activate
fi

# Import questions if database doesn't exist
if [ ! -f "data/quiz.db" ]; then
    echo "Importing questions..."
    python3 import_questions.py
fi

echo ""
echo "Starting AWS Quiz at http://localhost:5050"
echo "Press Ctrl+C to stop"
echo ""

python3 app.py
