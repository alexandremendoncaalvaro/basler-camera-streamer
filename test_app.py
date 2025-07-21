#!/usr/bin/env python3
"""
Teste simples para verificar se a aplicação está funcionando
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from video_source import VideoSourceFactory

    print("✓ video_source importado com sucesso")

    # Testa a factory
    source = VideoSourceFactory.create_source()
    if source is None:
        print("⚠ Nenhuma fonte de vídeo disponível (normal sem câmera ou vídeo)")
    else:
        print(f"✓ Fonte criada: {type(source).__name__}")

    # Testa import do Flask
    from flask import Flask

    print("✓ Flask importado com sucesso")

    # Testa OpenCV
    import cv2

    print(f"✓ OpenCV importado com sucesso - versão: {cv2.__version__}")

    print("\n🎉 Todos os imports estão funcionando!")
    print("\nPara testar a aplicação:")
    print("1. Faça upload de um vídeo através da interface web")
    print("2. Ou conecte uma câmera Basler")
    print("3. Execute: .venv/bin/python capture.py")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback

    traceback.print_exc()
