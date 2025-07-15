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
        cam = pylon.InstantCamera(
            pylon.TlFactory.GetInstance().CreateFirstDevice()
        )
        cam.Open()
        cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        conv = pylon.ImageFormatConverter()
        conv.OutputPixelFormat = pylon.PixelType_BGR8packed
        conv.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        self.camera = cam
        self.converter = conv

    def generate_frames(self):
        while True:
            res = self.camera.RetrieveResult(
                CAMERA_TIMEOUT_MS,
                pylon.TimeoutHandling_ThrowException
            )
            if not res.GrabSucceeded():
                res.Release()
                continue
            img = self.converter.Convert(res).Array
            res.Release()

            ok, buf = cv2.imencode(".jpg", img)
            if not ok:
                continue

            yield (
                b"--" + BOUNDARY.encode() + b"\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buf.tobytes() +
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
