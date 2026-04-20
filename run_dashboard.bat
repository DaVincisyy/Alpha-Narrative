@echo off
REM Streamlit Dashboard Launcher for Windows

echo ========================================
echo Sentiment Factor Analysis Dashboard
echo ========================================
echo.

REM Check if data exists
if not exist "data\processed\factor_data.parquet" (
    echo [ERROR] Data file not found!
    echo.
    echo Please run the pipeline first:
    echo   1. python src/sentiment_extractor.py
    echo.
    pause
    exit /b 1
)

echo [OK] Data file found
echo.
echo Starting Streamlit dashboard...
echo.
echo Dashboard will open in your browser at:
echo   http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo.

streamlit run app.py

pause
