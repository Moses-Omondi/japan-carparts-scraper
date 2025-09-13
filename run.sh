#!/bin/bash

# Japanese OEM Car Parts Scraper Runner
# This script activates the virtual environment and runs the scraper

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please set up the project first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Run the scraper using the virtual environment Python
echo "Running Japanese OEM Car Parts Scraper..."
echo "Project directory: $SCRIPT_DIR"
echo ""

./venv/bin/python main.py "$@"
