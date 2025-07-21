#!/usr/bin/env python3
"""
Servidor simplificado para teste sem dependências externas
"""

from flask import (
    Flask,
    Response,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
)
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "test_key"

UPLOAD_FOLDER = "/Users/alexandrealvaro/dev/estudio/basler-camera-streamer/uploads"
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Garante que o diretório de upload existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    uploaded_video = os.path.exists(os.path.join(UPLOAD_FOLDER, "current_video.mp4"))

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Streamer - Teste</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .upload-section {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 15px 0; }}
            .status {{ background: white; padding: 20px; border-radius: 8px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .btn {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }}
            .btn:hover {{ background: #0056b3; }}
            .upload-form {{ margin-top: 15px; }}
            .file-input {{ margin: 10px 0; }}
            .ok {{ color: #28a745; font-weight: bold; }}
            .error {{ color: #dc3545; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎥 Video Streamer - Teste</h1>
            
            <div class="upload-section">
                <h2>📁 Upload de Vídeo</h2>
                <p>Faça upload de um arquivo de vídeo para streaming em loop</p>
                <form class="upload-form" action="/upload" method="post" enctype="multipart/form-data">
                    <div class="file-input">
                        <input type="file" name="video" accept=".mp4,.avi,.mov,.mkv,.webm" required>
                    </div>
                    <button type="submit" class="btn">📤 Upload Vídeo</button>
                </form>
                <p><small>Formatos suportados: MP4, AVI, MOV, MKV, WebM</small></p>
            </div>
            
            <div class="status">
                <h2>📊 Status</h2>
                <p><strong>Vídeo Carregado:</strong> 
                    <span class="{'ok' if uploaded_video else 'error'}">
                        {'Sim' if uploaded_video else 'Não'}
                    </span>
                </p>
                {f'<p><a href="/start_stream" class="btn">🎬 Iniciar Stream</a></p>' if uploaded_video else ''}
            </div>
        </div>
    </body>
    </html>
    """


@app.route("/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return redirect(url_for("home"))

    file = request.files["video"]
    if file.filename == "":
        return redirect(url_for("home"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        video_path = os.path.join(UPLOAD_FOLDER, "current_video.mp4")

        # Remove o vídeo anterior se existir
        if os.path.exists(video_path):
            os.remove(video_path)

        file.save(video_path)
        return redirect(url_for("home"))
    else:
        return redirect(url_for("home"))


@app.route("/start_stream")
def start_stream():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Streaming Iniciado</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; text-align: center; }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin: 10px; }
        </style>
    </head>
    <body>
        <h1>✅ Upload realizado com sucesso!</h1>
        <p>O vídeo foi carregado e está pronto para streaming.</p>
        <p>Agora você pode executar a aplicação principal:</p>
        <code>.venv/bin/python capture.py</code>
        <br><br>
        <a href="/" class="btn">← Voltar</a>
    </body>
    </html>
    """


if __name__ == "__main__":
    print("🎬 Servidor de teste iniciado!")
    print("📍 Acesse: http://localhost:8080")
    print("📁 Faça upload de um vídeo para testar")
    app.run(host="0.0.0.0", port=8080, debug=True)
