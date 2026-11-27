"""Grabador de pantalla: captura el proceso Selenium como video MP4.

Captura la ventana del navegador Chrome (o el monitor donde esté posicionado)
utilizando Selenium get_window_rect y mss / OpenCV sin dependencias externas complejas.
"""
import threading
import time
from pathlib import Path

import cv2
import mss
import numpy as np

RECORDINGS_DIR = Path(__file__).parent / "static" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class ScreenRecorder(threading.Thread):
    """Graba la pantalla o la región de Chrome directamente en MP4 con OpenCV."""

    def __init__(self, filename="recording", fps=6, driver=None):
        super().__init__(daemon=True)
        self.fps = fps
        self.filename = filename
        self.driver = driver
        self.stop_flag = threading.Event()
        self.video_path = RECORDINGS_DIR / f"{self.filename}.mp4"

    def _determine_capture_bbox(self, sct):
        """Calcula las coordenadas de captura basadas en la ventana de Chrome o el monitor principal."""
        monitors = sct.monitors

        # 1. Si tenemos driver, intentar obtener el rect de la ventana de Chrome
        if self.driver:
            try:
                rect = self.driver.get_window_rect()
                x = rect.get("x", 0)
                y = rect.get("y", 0)
                w = rect.get("width", 1440)
                h = rect.get("height", 900)
                if w > 100 and h > 100:
                    return {"left": int(x), "top": int(y), "width": int(w), "height": int(h)}
            except Exception:
                pass

        # 2. Si no o falló, buscar el monitor principal o el monitor donde esté (evitar monitor 1 si es secundario)
        for m in monitors[1:]:
            if m.get("is_primary"):
                return m

        # 3. Fallback: monitor 2 o monitor 0
        if len(monitors) > 2:
            return monitors[2]
        elif len(monitors) > 1:
            return monitors[1]
        return monitors[0]

    def run(self):
        interval = 1.0 / self.fps
        writer = None
        try:
            with mss.mss() as sct:
                bbox = self._determine_capture_bbox(sct)
                width = bbox["width"]
                height = bbox["height"]

                # Asegurar dimensiones pares para codecs de video
                if width % 2 != 0:
                    width -= 1
                    bbox["width"] = width
                if height % 2 != 0:
                    height -= 1
                    bbox["height"] = height

                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(str(self.video_path), fourcc, self.fps, (width, height))

                while not self.stop_flag.is_set():
                    start = time.monotonic()
                    try:
                        # Si tenemos driver, actualizar posición si se movió o redimensionó
                        if self.driver:
                            try:
                                r = self.driver.get_window_rect()
                                cur_w = r.get("width", width)
                                cur_h = r.get("height", height)
                                if cur_w % 2 != 0: cur_w -= 1
                                if cur_h % 2 != 0: cur_h -= 1
                                bbox["left"] = int(r.get("x", bbox["left"]))
                                bbox["top"] = int(r.get("y", bbox["top"]))
                                # Solo redimensionar si coincide con el writer
                                bbox["width"] = width
                                bbox["height"] = height
                            except Exception:
                                pass

                        raw = sct.grab(bbox)
                        frame = np.array(raw)[:, :, :3]  # BGRA -> BGR
                        if frame.shape[1] != width or frame.shape[0] != height:
                            frame = cv2.resize(frame, (width, height))
                        writer.write(frame)
                    except Exception:
                        pass
                    elapsed = time.monotonic() - start
                    remaining = interval - elapsed
                    if remaining > 0:
                        self.stop_flag.wait(remaining)
        except Exception:
            self.video_path = None
        finally:
            if writer is not None:
                writer.release()

    def stop(self):
        self.stop_flag.set()
        self.join(timeout=15)
        return self.video_path

    def get_video_url(self):
        if self.video_path and self.video_path.exists() and self.video_path.stat().st_size > 0:
            return f"/static/recordings/{self.video_path.name}"
        return None
