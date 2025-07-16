import os
import atexit
import threading
import time
from datetime import datetime

from flask import Flask, Response, abort
from pypylon import pylon
import cv2

BOUNDARY = os.getenv("FRAME_BOUNDARY", "frame")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8080))
TIMEOUT_MS = int(os.getenv("CAMERA_TIMEOUT_MS", 1000))
FRAME_RATE = float(os.getenv("ACQUISITION_FRAME_RATE", "30.0"))
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", 3))


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


class CameraController:
    def __init__(self):
        self._camera = self._create_camera()
        self._converter = self._create_converter()
        self._running = True

    def _create_camera(self):
        tl_factory = pylon.TlFactory.GetInstance()
        device = tl_factory.CreateFirstDevice()
        camera = pylon.InstantCamera(device)
        camera.Open()
        self._configure_camera(camera)
        return camera

    def _configure_camera(self, camera):
        camera.AcquisitionMode.SetValue("Continuous")
        camera.ExposureAuto.SetValue("Continuous")
        camera.GainAuto.SetValue("Continuous")
        camera.AcquisitionFrameRateEnable.SetValue(True)
        camera.AcquisitionFrameRate.SetValue(FRAME_RATE)

    def _create_converter(self):
        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        return converter

    def start_grabbing(self):
        self._camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    def is_grabbing(self):
        return self._camera.IsGrabbing()

    def is_open(self):
        return self._camera.IsOpen()

    def capture_frame(self):
        if not self.is_grabbing():
            return None

        result = self._camera.RetrieveResult(
            TIMEOUT_MS, pylon.TimeoutHandling_ThrowException
        )

        if not result.GrabSucceeded():
            result.Release()
            return None

        img = self._converter.Convert(result).Array
        result.Release()

        return self._encode_frame(img)

    def _encode_frame(self, img):
        ok, buf = cv2.imencode(".jpg", img)
        if not ok:
            return None

        header = (
            b"--" + BOUNDARY.encode() + b"\r\n" + b"Content-Type: image/jpeg\r\n\r\n"
        )
        return header + buf.tobytes() + b"\r\n"

    def close(self):
        self._running = False
        if self.is_grabbing():
            self._camera.StopGrabbing()
        if self.is_open():
            self._camera.Close()


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


class CameraStreamer:
    def __init__(self):
        self._camera = CameraController()
        self._buffer = FrameBuffer()
        self._connections = ConnectionManager(MAX_CONNECTIONS)
        self._status = StatusTracker()
        self._capture_thread = None
        self._start_capture_thread()

    def _start_capture_thread(self):
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        self._camera.start_grabbing()

    def _capture_loop(self):
        while self._camera.is_grabbing():
            try:
                frame = self._camera.capture_frame()
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
            while self._camera.is_grabbing():
                frame = self._buffer.get()
                if frame:
                    yield frame
        except GeneratorExit:
            pass
        finally:
            self._connections.release()

    def get_status(self):
        return {
            "camera_connected": self._camera.is_open(),
            "grabbing_active": self._camera.is_grabbing(),
            "active_connections": self._connections.get_count(),
            "max_connections": MAX_CONNECTIONS,
            "fps": round(self._status.get_fps(), 2),
            "total_frames": self._status.get_frame_count(),
            "uptime": str(self._status.get_uptime()).split(".")[0],
            "configured_fps": FRAME_RATE,
        }

    def close(self):
        self._camera.close()


class StatusPageRenderer:
    def render(self, status):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Basler Camera Streamer - Status</title>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="5">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .status {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .ok {{ color: #28a745; }}
                .warning {{ color: #ffc107; }}
                .error {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <h1>Basler Camera Streamer</h1>
            
            <div class="status">
                <h2>Status da Câmera</h2>
                <p><strong>Conectada:</strong> <span class="{'ok' if status['camera_connected'] else 'error'}">{'Sim' if status['camera_connected'] else 'Não'}</span></p>
                <p><strong>Captura Ativa:</strong> <span class="{'ok' if status['grabbing_active'] else 'error'}">{'Sim' if status['grabbing_active'] else 'Não'}</span></p>
                <p><strong>FPS Configurado:</strong> {status['configured_fps']}</p>
                <p><strong>FPS Atual:</strong> {status['fps']}</p>
                <p><strong>Total de Frames:</strong> {status['total_frames']}</p>
            </div>
            
            <div class="status">
                <h2>Conexões</h2>
                <p><strong>Ativas:</strong> 
                    <span class="{'ok' if status['active_connections'] < status['max_connections'] else 'warning'}">
                        {status['active_connections']}/{status['max_connections']}
                    </span>
                </p>
            </div>
            
            <div class="status">
                <h2>Sistema</h2>
                <p><strong>Uptime:</strong> {status['uptime']}</p>
                <p><strong>Endpoint:</strong> <a href="/video_feed">/video_feed</a></p>
            </div>
            
            <p><small>Atualização automática a cada 5 segundos</small></p>
        </body>
        </html>
        """


streamer = CameraStreamer()
status_renderer = StatusPageRenderer()
atexit.register(streamer.close)

app = Flask(__name__)


@app.route("/video_feed")
def video_feed():
    if not streamer.can_connect():
        abort(503, "Limite de conexões atingido")

    return Response(
        streamer.generate_frames(),
        mimetype=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
    )


@app.route("/")
def home():
    status = streamer.get_status()
    return status_renderer.render(status)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
