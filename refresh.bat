@echo off
cd /d "%~dp0"
echo ========================================
echo  Garmini - Refreshing Garmin Data
echo ========================================
python pull.py
if %ERRORLEVEL% NEQ 0 (
    echo [!] Error during pull. Check your connection or API key.
    pause
    exit /b %ERRORLEVEL%
)
python build.py
if %ERRORLEVEL% NEQ 0 (
    echo [!] Error during build.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [OK] Dashboard updated successfully!
echo Opening dashboard in default browser...
start "" "dashboard.html"
