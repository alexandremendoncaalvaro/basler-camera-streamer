import os
import cv2
import time
import threading
from abc import ABC, abstractmethod


class VideoSource(ABC):
    def __init__(self):
        self._running = True

    @abstractmethod
    def start_capture(self):
        pass

    @abstractmethod
    def capture_frame(self):
        pass

    @abstractmethod
    def is_available(self):
        pass

    @abstractmethod
    def close(self):
        pass


class BaslerCameraSource(VideoSource):
    def __init__(self):
        super().__init__()
        try:
            from pypylon import pylon

            self._pylon = pylon
            self._camera = self._create_camera()
            self._converter = self._create_converter()
        except ImportError:
            raise RuntimeError("pypylon not available")

    def _create_camera(self):
        tl_factory = self._pylon.TlFactory.GetInstance()
        device = tl_factory.CreateFirstDevice()
        camera = self._pylon.InstantCamera(device)
        camera.Open()
        self._configure_camera(camera)
        return camera

    def _configure_camera(self, camera):
        from capture import (
            ACQUISITION_MODE,
            ACQUISITION_FRAME_RATE_ENABLE,
            FRAME_RATE,
            EXPOSURE_AUTO,
            EXPOSURE_TIME,
            GAIN_AUTO,
            GAIN,
        )

        camera.AcquisitionMode.SetValue(ACQUISITION_MODE)
        camera.AcquisitionFrameRateEnable.SetValue(ACQUISITION_FRAME_RATE_ENABLE)

        if ACQUISITION_FRAME_RATE_ENABLE:
            camera.AcquisitionFrameRate.SetValue(FRAME_RATE)

        camera.ExposureAuto.SetValue(EXPOSURE_AUTO)
        if EXPOSURE_AUTO == "Off":
            camera.ExposureTime.SetValue(EXPOSURE_TIME)

        camera.GainAuto.SetValue(GAIN_AUTO)
        if GAIN_AUTO == "Off":
            camera.Gain.SetValue(GAIN)

    def _create_converter(self):
        converter = self._pylon.ImageFormatConverter()
        converter.OutputPixelFormat = self._pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = self._pylon.OutputBitAlignment_MsbAligned
        return converter

    def start_capture(self):
        from capture import GRAB_STRATEGY

        grab_strategy = getattr(self._pylon, f"GrabStrategy_{GRAB_STRATEGY}")
        self._camera.StartGrabbing(grab_strategy)

    def capture_frame(self):
        from capture import TIMEOUT_MS

        if not self._camera.IsGrabbing():
            return None

        result = self._camera.RetrieveResult(
            TIMEOUT_MS, self._pylon.TimeoutHandling_ThrowException
        )

        if not result.GrabSucceeded():
            result.Release()
            return None

        img = self._converter.Convert(result).Array
        result.Release()
        return img

    def is_available(self):
        return self._camera.IsOpen() and self._camera.IsGrabbing()

    def close(self):
        self._running = False
        if self._camera.IsGrabbing():
            self._camera.StopGrabbing()
        if self._camera.IsOpen():
            self._camera.Close()


class VideoFileSource(VideoSource):
    def __init__(self, video_path):
        super().__init__()
        self._video_path = video_path
        self._cap = None
        self._frame_rate = 30.0
        self._last_frame_time = 0
        self._lock = threading.Lock()

    def start_capture(self):
        self._cap = cv2.VideoCapture(self._video_path)
        if self._cap.isOpened():
            self._frame_rate = self._cap.get(cv2.CAP_PROP_FPS) or 30.0

    def capture_frame(self):
        if not self.is_available():
            return None

        with self._lock:
            current_time = time.time()
            frame_interval = 1.0 / self._frame_rate

            if current_time - self._last_frame_time < frame_interval:
                time.sleep(frame_interval - (current_time - self._last_frame_time))

            ret, frame = self._cap.read()

            if not ret:
                # Reinicia o vídeo para loop
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()

            self._last_frame_time = time.time()
            return frame if ret else None

    def is_available(self):
        return self._cap is not None and self._cap.isOpened()

    def close(self):
        self._running = False
        if self._cap:
            self._cap.release()


class VideoSourceFactory:
    @staticmethod
    def create_source():
        uploaded_video_path = "/Users/alexandrealvaro/dev/estudio/basler-camera-streamer/uploads/current_video.mp4"

        # Primeiro tenta usar vídeo uploadado
        if os.path.exists(uploaded_video_path):
            try:
                source = VideoFileSource(uploaded_video_path)
                source.start_capture()
                if source.is_available():
                    return source
                else:
                    print(f"Video file {uploaded_video_path} exists but failed to load")
            except Exception as e:
                print(f"Error loading video file: {e}")

        # Caso contrário tenta usar câmera Basler
        try:
            source = BaslerCameraSource()
            source.start_capture()
            return source
        except (ImportError, RuntimeError) as e:
            print(f"Basler camera not available: {e}")
            return None
