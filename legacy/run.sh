#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install beautifulsoup4 requests lxml reportlab pillow pandas
    echo "✅ Setup completed!"
fi

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "🚗 Japanese Car Parts Scraper"
    echo ""
    echo "Usage:"
    echo "  ./run.sh --sample-only                    # Test with sample data"
    echo "  ./run.sh https://www.example.com/         # Scrape a website"
    echo "  ./run.sh site1.com site2.com             # Multiple sites"
    echo ""
    exit 0
fi

# Run the scraper
echo "🚗 Running scraper..."
./venv/bin/python main.py "$@"
