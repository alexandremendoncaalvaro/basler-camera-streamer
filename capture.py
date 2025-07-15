import os
import atexit

from flask import Flask, Response
from pypylon import pylon
import cv2

BOUNDARY    = os.getenv("FRAME_BOUNDARY", "frame")
HOST        = os.getenv("HOST", "0.0.0.0")
PORT        = int(os.getenv("PORT", 8080))
TIMEOUT_MS  = int(os.getenv("CAMERA_TIMEOUT_MS", 1000))
FRAME_RATE  = float(os.getenv("ACQUISITION_FRAME_RATE", "30.0"))

class CameraStreamer:
    def __init__(self):
        tl_factory = pylon.TlFactory.GetInstance()
        device     = tl_factory.CreateFirstDevice()
        cam        = pylon.InstantCamera(device)
        cam.Open()
        cam.AcquisitionMode.SetValue("Continuous")
        cam.ExposureAuto.SetValue("Continuous")
        cam.GainAuto.SetValue("Continuous")
        cam.AcquisitionFrameRateEnable.SetValue(True)
        cam.AcquisitionFrameRate.SetValue(FRAME_RATE)
        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat      = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment     = pylon.OutputBitAlignment_MsbAligned
        cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        self.camera    = cam
        self.converter = converter

    def generate_frames(self):
        while self.camera.IsGrabbing():
            result = self.camera.RetrieveResult(
                TIMEOUT_MS,
                pylon.TimeoutHandling_ThrowException
            )
            if not result.GrabSucceeded():
                result.Release()
                continue
            img = self.converter.Convert(result).Array
            result.Release()

            ok, buf = cv2.imencode(".jpg", img)
            if not ok:
                continue

            header = b"--" + BOUNDARY.encode() + b"\r\n" \
                   + b"Content-Type: image/jpeg\r\n\r\n"
            yield header + buf.tobytes() + b"\r\n"

    def close(self):
        if self.camera.IsGrabbing():
            self.camera.StopGrabbing()
        if self.camera.IsOpen():
            self.camera.Close()

streamer = CameraStreamer()
atexit.register(streamer.close)

app = Flask(__name__)

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
    