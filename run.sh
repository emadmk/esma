#!/bin/bash
# Food Cost Analysis App - Startup Script

echo "=== سامانه آنالیز هزینه غذا ==="
echo ""

# Check if database exists, if not, extract data from Excel
if [ ! -f "app/food_cost.db" ]; then
    echo "در حال استخراج دیتا از فایل اکسل..."
    python3 app/extract_data.py
    echo ""
fi

# Run with gunicorn for production
echo "سرور در حال اجراست..."
echo "آدرس: http://0.0.0.0:5000"
echo ""

if command -v gunicorn &> /dev/null; then
    gunicorn -w 2 -b 0.0.0.0:5000 app.main:app
else
    python3 -m flask --app app.main run --host 0.0.0.0 --port 5000
fi
