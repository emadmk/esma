#!/bin/bash
set -e

echo "=== Food Cost Analysis System ==="

# Install dependencies
pip install -r requirements.txt

# Copy .xls to .xlsx (the file is actually xlsx format)
if [ ! -f "DOC-20251215-WA0000.xlsx" ] && [ -f "DOC-20251215-WA0000.xls" ]; then
    cp DOC-20251215-WA0000.xls DOC-20251215-WA0000.xlsx
    echo "Converted .xls to .xlsx"
fi

# Extract data from Excel
echo "Extracting data from Excel..."
python3 app/extract_data.py

# Run the server
echo "Starting server on port 8080..."
python3 app/main.py
