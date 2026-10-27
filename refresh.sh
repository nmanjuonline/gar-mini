#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "========================================"
echo " Garmini - Refreshing Garmin Data"
echo "========================================"
python3 pull.py
if [ $? -ne 0 ]; then
    echo "[!] Error during pull."
    exit 1
fi
python3 build.py
if [ $? -ne 0 ]; then
    echo "[!] Error during build."
    exit 1
fi
echo ""
echo "[OK] Dashboard updated successfully!"
