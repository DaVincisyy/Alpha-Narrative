#!/bin/bash
# Streamlit Dashboard Launcher for Linux/Mac

echo "========================================"
echo "Sentiment Factor Analysis Dashboard"
echo "========================================"
echo ""

# Check if data exists
if [ ! -f "data/processed/factor_data.parquet" ]; then
    echo "[ERROR] Data file not found!"
    echo ""
    echo "Please run the pipeline first:"
    echo "  1. python src/sentiment_extractor.py"
    echo ""
    exit 1
fi

echo "[OK] Data file found"
echo ""
echo "Starting Streamlit dashboard..."
echo ""
echo "Dashboard will open in your browser at:"
echo "  http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run app.py
