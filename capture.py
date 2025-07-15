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
        camera = pylon.InstantCamera(
            pylon.TlFactory.GetInstance().CreateFirstDevice()
        )
        camera.Open()
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        self.camera = camera

    def generate_frames(self):
        while True:
            result = self.camera.RetrieveResult(
                CAMERA_TIMEOUT_MS,
                pylon.TimeoutHandling_ThrowException
            )
            if not result.GrabSucceeded():
                result.Release()
                continue
            img = result.Array
            result.Release()

            success, buffer = cv2.imencode(".jpg", img)
            if not success:
                continue

            yield (
                b"--" + BOUNDARY.encode() + b"\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes() +
                b"\r\n"
            )

    def __del__(self):
        if self.camera.IsGrabbing():
            self.camera.StopGrabbing()
        if self.camera.IsOpen():
            self.camera.Close()

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
