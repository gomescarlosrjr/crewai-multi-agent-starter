#!/bin/bash
# Script para executar o Dividend Analyst Streamlit App

echo "🚀 Iniciando Dividend Analyst..."
echo ""

# Ativa o ambiente virtual
source .venv/bin/activate

# Executa o Streamlit
streamlit run streamlit_app.py

# Mensagem de saída
echo ""
echo "👋 App encerrado. Até logo!"


