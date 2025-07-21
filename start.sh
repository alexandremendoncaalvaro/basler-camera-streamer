#!/bin/bash

echo "🎬 Basler Camera Streamer - Inicialização"
echo "========================================"

# Verifica se está no diretório correto
if [ ! -f "capture.py" ]; then
    echo "❌ Execute este script no diretório do projeto"
    exit 1
fi

# Verifica se o ambiente virtual existe
if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado"
    echo "   Execute: python -m venv .venv"
    exit 1
fi

echo "🔧 Ativando ambiente virtual..."
source .venv/bin/activate

echo "📋 Dependências instaladas:"
pip list | grep -E "(flask|opencv|numpy)"

echo ""
echo "🎯 Opções disponíveis:"
echo ""
echo "1️⃣  Para TESTE SIMPLES (upload de vídeo):"
echo "   .venv/bin/python test_server.py"
echo ""
echo "2️⃣  Para APLICAÇÃO PRINCIPAL:"
echo "   .venv/bin/python capture.py"
echo ""
echo "📍 Depois acesse: http://localhost:8080"
echo ""
echo "💡 Dica: Se não tiver câmera Basler, use a opção 1 primeiro!"
echo "   Faça upload de um vídeo e depois rode a opção 2."
echo ""
echo "🎬 Iniciando servidor de teste..."
.venv/bin/python test_server.py
