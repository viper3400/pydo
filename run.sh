#!/bin/bash

# PyTodo - Simple script to run the app

# Activate virtual environment if it exists
if [ -d "myenv" ]; then
    source myenv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠ Virtual environment not found. Creating one..."
    python3 -m venv myenv
    source myenv/bin/activate
    echo "✓ Virtual environment created and activated"

    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo "✓ Dependencies installed"
fi

# Run the app
echo ""
echo "🚀 Starting PyTodo..."
echo "📱 Open your browser and navigate to: http://127.0.0.1:5000"
echo ""
python app.py
