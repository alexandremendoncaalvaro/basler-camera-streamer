import os
import atexit
import threading
import time
from datetime import datetime

from flask import (
    Flask,
    Response,
    abort,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
)
from werkzeug.utils import secure_filename
import cv2
from video_source import VideoSourceFactory

BOUNDARY = os.getenv("FRAME_BOUNDARY", "frame")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8080))
TIMEOUT_MS = int(os.getenv("CAMERA_TIMEOUT_MS", 1000))
FRAME_RATE = float(os.getenv("ACQUISITION_FRAME_RATE", "30.0"))
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", 3))
UPLOAD_FOLDER = os.getenv(
    "UPLOAD_FOLDER", "/Users/alexandrealvaro/dev/estudio/basler-camera-streamer/uploads"
)
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

# Camera parameters
ACQUISITION_MODE = os.getenv("ACQUISITION_MODE", "Continuous")
GRAB_STRATEGY = os.getenv("GRAB_STRATEGY", "LatestImageOnly")
ACQUISITION_FRAME_RATE_ENABLE = (
    os.getenv("ACQUISITION_FRAME_RATE_ENABLE", "True").lower() == "true"
)

# Exposure and Gain
EXPOSURE_AUTO = os.getenv("EXPOSURE_AUTO", "Continuous")
EXPOSURE_TIME = float(os.getenv("EXPOSURE_TIME", "5000"))  # microseconds
GAIN_AUTO = os.getenv("GAIN_AUTO", "Continuous")
GAIN = float(os.getenv("GAIN", "0"))  # dB

# Image adjustments
IMAGE_CONTRAST = float(os.getenv("IMAGE_CONTRAST", "1.0"))
IMAGE_BRIGHTNESS = int(os.getenv("IMAGE_BRIGHTNESS", "0"))


class FrameBuffer:
    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None
        self._event = threading.Event()

    def put(self, frame):
        with self._lock:
            self._frame = frame
            self._event.set()

    def get(self, timeout=1.0):
        if self._event.wait(timeout):
            with self._lock:
                return self._frame
        return None


class ConnectionManager:
    def __init__(self, max_connections):
        self._max_connections = max_connections
        self._count = 0
        self._lock = threading.Lock()

    def can_connect(self):
        with self._lock:
            return self._count < self._max_connections

    def acquire(self):
        with self._lock:
            if self._count < self._max_connections:
                self._count += 1
                return True
            return False

    def release(self):
        with self._lock:
            if self._count > 0:
                self._count -= 1

    def get_count(self):
        with self._lock:
            return self._count


class VideoController:
    def __init__(self):
        self._source = VideoSourceFactory.create_source()
        self._running = True

    def start_capture(self):
        if self._source:
            self._source.start_capture()

    def is_available(self):
        return self._source and self._source.is_available()

    def capture_frame(self):
        if not self.is_available():
            return None

        img = self._source.capture_frame()
        if img is None:
            return None

        return self._encode_frame(img)

    def _encode_frame(self, img):
        # Apply image adjustments if needed
        if IMAGE_CONTRAST != 1.0 or IMAGE_BRIGHTNESS != 0:
            img = self._apply_image_adjustments(img)

        ok, buf = cv2.imencode(".jpg", img)
        if not ok:
            return None

        header = (
            b"--" + BOUNDARY.encode() + b"\r\n" + b"Content-Type: image/jpeg\r\n\r\n"
        )
        return header + buf.tobytes() + b"\r\n"

    def _apply_image_adjustments(self, img):
        # Apply contrast and brightness: new_img = contrast * img + brightness
        adjusted = cv2.convertScaleAbs(img, alpha=IMAGE_CONTRAST, beta=IMAGE_BRIGHTNESS)
        return adjusted

    def close(self):
        self._running = False
        if self._source:
            self._source.close()

    def get_source_type(self):
        if not self._source:
            return "None"
        return type(self._source).__name__


class StatusTracker:
    def __init__(self):
        self._start_time = datetime.now()
        self._frame_count = 0
        self._last_frame_time = time.time()
        self._fps_samples = []
        self._lock = threading.Lock()

    def record_frame(self):
        current_time = time.time()
        with self._lock:
            self._frame_count += 1
            frame_time = current_time - self._last_frame_time
            self._fps_samples.append(frame_time)
            self._last_frame_time = current_time

            # Keep only last 30 samples
            if len(self._fps_samples) > 30:
                self._fps_samples.pop(0)

    def get_fps(self):
        with self._lock:
            if len(self._fps_samples) < 2:
                return 0.0
            return len(self._fps_samples) / sum(self._fps_samples)

    def get_frame_count(self):
        with self._lock:
            return self._frame_count

    def get_uptime(self):
        return datetime.now() - self._start_time


class VideoStreamer:
    def __init__(self):
        self._video_controller = VideoController()
        self._buffer = FrameBuffer()
        self._connections = ConnectionManager(MAX_CONNECTIONS)
        self._status = StatusTracker()
        self._capture_thread = None
        self._start_capture_thread()

    def _start_capture_thread(self):
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        self._video_controller.start_capture()

    def _capture_loop(self):
        while self._video_controller.is_available():
            try:
                frame = self._video_controller.capture_frame()
                if frame:
                    self._buffer.put(frame)
                    self._status.record_frame()
            except Exception as e:
                print(f"Erro na captura: {e}")
                time.sleep(0.1)

    def can_connect(self):
        return self._connections.can_connect()

    def generate_frames(self):
        if not self._connections.acquire():
            return

        try:
            while self._video_controller.is_available():
                frame = self._buffer.get()
                if frame:
                    yield frame
        except GeneratorExit:
            pass
        finally:
            self._connections.release()

    def get_status(self):
        return {
            "source_type": self._video_controller.get_source_type(),
            "source_available": self._video_controller.is_available(),
            "active_connections": self._connections.get_count(),
            "max_connections": MAX_CONNECTIONS,
            "fps": round(self._status.get_fps(), 2),
            "total_frames": self._status.get_frame_count(),
            "uptime": str(self._status.get_uptime()).split(".")[0],
            "configured_fps": FRAME_RATE,
        }

    def restart_with_new_source(self):
        # Para a captura atual
        self._video_controller.close()

        # Cria novo controller
        self._video_controller = VideoController()

        # Reinicia thread de captura
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=1.0)

        self._start_capture_thread()

    def close(self):
        self._video_controller.close()


class StatusPageRenderer:
    def render(self, status):
        source_status = self._get_source_status(
            status["source_type"], status["source_available"]
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Basler Camera Streamer - Status</title>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="5">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .status {{ background: white; padding: 20px; border-radius: 8px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .upload-section {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 15px 0; }}
                .ok {{ color: #28a745; font-weight: bold; }}
                .warning {{ color: #ffc107; font-weight: bold; }}
                .error {{ color: #dc3545; font-weight: bold; }}
                .btn {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }}
                .btn:hover {{ background: #0056b3; }}
                .upload-form {{ margin-top: 15px; }}
                .file-input {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎥 Video Streamer</h1>
                
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
                    <h2>📊 Status da Fonte de Vídeo</h2>
                    <p><strong>Tipo:</strong> <span class="{source_status['class']}">{source_status['text']}</span></p>
                    <p><strong>Disponível:</strong> <span class="{'ok' if status['source_available'] else 'error'}">{'Sim' if status['source_available'] else 'Não'}</span></p>
                    <p><strong>FPS Configurado:</strong> {status['configured_fps']}</p>
                    <p><strong>FPS Atual:</strong> {status['fps']}</p>
                    <p><strong>Total de Frames:</strong> {status['total_frames']}</p>
                </div>
                
                <div class="status">
                    <h2>🔗 Conexões</h2>
                    <p><strong>Ativas:</strong> 
                        <span class="{'ok' if status['active_connections'] < status['max_connections'] else 'warning'}">
                            {status['active_connections']}/{status['max_connections']}
                        </span>
                    </p>
                </div>
                
                <div class="status">
                    <h2>⚙️ Sistema</h2>
                    <p><strong>Uptime:</strong> {status['uptime']}</p>
                    <p><strong>Endpoint:</strong> <a href="/video_feed">/video_feed</a></p>
                    <p><strong>Preview:</strong> <a href="/preview">🖼️ Ver Preview</a></p>
                </div>
                
                <p><small>Atualização automática a cada 5 segundos</small></p>
            </div>
        </body>
        </html>
        """

    def _get_source_status(self, source_type, is_available):
        if source_type == "VideoFileSource":
            return {
                "text": "📹 Arquivo de Vídeo",
                "class": "ok" if is_available else "error",
            }
        elif source_type == "BaslerCameraSource":
            return {
                "text": "📷 Câmera Basler",
                "class": "ok" if is_available else "error",
            }
        else:
            return {"text": "❌ Nenhuma fonte disponível", "class": "error"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Garante que o diretório de upload existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

streamer = VideoStreamer()
status_renderer = StatusPageRenderer()
atexit.register(streamer.close)

app = Flask(__name__)
app.secret_key = "video_streamer_secret_key"


@app.route("/video_feed")
def video_feed():
    if not streamer.can_connect():
        abort(503, "Limite de conexões atingido")

    return Response(
        streamer.generate_frames(),
        mimetype=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
    )


@app.route("/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        flash("Nenhum arquivo selecionado")
        return redirect(url_for("home"))

    file = request.files["video"]
    if file.filename == "":
        flash("Nenhum arquivo selecionado")
        return redirect(url_for("home"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        video_path = os.path.join(UPLOAD_FOLDER, "current_video.mp4")

        # Remove o vídeo anterior se existir
        if os.path.exists(video_path):
            os.remove(video_path)

        file.save(video_path)
        flash("Vídeo enviado com sucesso! Reiniciando stream...")

        # Reinicia o streamer com nova fonte
        streamer.restart_with_new_source()

        return redirect(url_for("home"))
    else:
        flash("Formato de arquivo não suportado")
        return redirect(url_for("home"))


@app.route("/preview")
def preview():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Stream Preview</title>
        <meta charset="UTF-8">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 20px; 
                background: #f5f5f5;
                text-align: center;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            img {
                max-width: 100%;
                border: 2px solid #ddd;
                border-radius: 8px;
            }
            .btn {
                background: #007bff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin: 10px;
            }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎥 Video Stream Preview</h1>
            <img src="/video_feed" alt="Video Stream">
            <br>
            <a href="/" class="btn">← Voltar ao Status</a>
        </div>
    </body>
    </html>
    """


@app.route("/")
def home():
    status = streamer.get_status()
    return status_renderer.render(status)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
