import os

from flask import Flask, Response
from pypylon import pylon
import cv2

BOUNDARY = os.getenv("FRAME_BOUNDARY", "frame")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8080))
CAMERA_TIMEOUT_MS = int(os.getenv("CAMERA_TIMEOUT_MS", 1000))

class CameraStreamer:
    def __init__(self):
        self.camera = pylon.InstantCamera(
            pylon.TlFactory.GetInstance().CreateFirstDevice()
        )
        self.camera.Open()

    def generate_frames(self):
        while self.camera.IsGrabbing():
            result = self.camera.GrabOne(CAMERA_TIMEOUT_MS)
            if not result.GrabSucceeded():
                return
            buffer = cv2.imencode(".jpg", result.Array)[1]
            yield (
                f"--{BOUNDARY}\r\n"
                "Content-Type: image/jpeg\r\n\r\n"
            ).encode() + buffer.tobytes() + b"\r\n"


app = Flask(__name__)
streamer = CameraStreamer()

@app.route("/video_feed")
def video_feed():
    return Response(
        streamer.generate_frames(),
        mimetype=f"multipart/x-mixed-replace; boundary={BOUNDARY}"
    )

@app.route("/")
def home():
    return "Bem vindo!"


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)

