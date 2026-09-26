#!/bin/bash
# Script to run the Dividend Analyst Streamlit app

echo "🚀 Starting Dividend Analyst..."
echo ""

# Activate the virtual environment
source .venv/bin/activate

# Run Streamlit
streamlit run streamlit_app.py

# Exit message
echo ""
echo "👋 App stopped. See you!"
