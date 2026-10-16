"""Reader thread for authenticated MJPEG streams provided by our Android companion app."""
import requests
import threading
from PySide6.QtCore import QThread, Signal


class MJPEGReader(QThread):
    jpeg_received = Signal(bytes)
    error = Signal(str)
    stopped = Signal()

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self._running = True
        self._response = None
        self._latest_lock = threading.Lock()
        self._latest_jpeg = None

    def pop_latest(self):
        # Fixed size queue: old frames get discarded if the GUI is busy.
        with self._latest_lock:
            result = self._latest_jpeg
            self._latest_jpeg = None
            return result

    def stop(self):
        self._running = False
        if self._response is not None:
            try: self._response.close()
            except Exception: pass

    def run(self):
        buffer = bytearray()
        try:
            with requests.get(self.url, stream=True, timeout=(4, 6)) as resp:
                self._response = resp
                resp.raise_for_status()
                for chunk in resp.iter_content(8192):
                    if not self._running: break
                    if not chunk: continue
                    buffer.extend(chunk)
                    while True:
                        start = buffer.find(b'\xff\xd8')
                        if start < 0:
                            if len(buffer)>1024*1024: buffer.clear()
                            break
                        end = buffer.find(b'\xff\xd9', start+2)
                        if end < 0:
                            if start>0: del buffer[:start]
                            if len(buffer)>8*1024*1024: buffer.clear()
                            break
                        jpeg = bytes(buffer[start:end+2])
                        del buffer[:end+2]
                        with self._latest_lock:
                            self._latest_jpeg = jpeg
        except Exception as e:
            if self._running: self.error.emit(str(e))
        finally:
            self._response = None
            self.stopped.emit()
