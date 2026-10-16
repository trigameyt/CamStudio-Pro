"""Non-blocking USB discovery for CamStudio Pro on Windows.

Detect only one authorized physical ADB device. USB debugging permission
must have been granted explicitly on Android; this cannot bypass it.
"""
from __future__ import annotations
import threading
import subprocess

from PySide6.QtCore import QObject,QTimer,Signal
from usb_transport import find_adb,adb_run,UsbConnectionError


def usb_device_state():
    """Return (ready, message) without leaking pairing credentials."""
    try:
        adb=find_adb()
        output=adb_run(adb,['devices','-l'],timeout=4)
    except UsbConnectionError as e:
        return False,str(e)
    lines=[s.strip() for s in output.splitlines()[1:] if s.strip()]
    usb=[]
    unauthorized=[]
    for line in lines:
        parts=line.split()
        if len(parts)<2:
            continue
        serial,state=parts[:2]
        if serial.startswith('emulator-') or ':' in serial:
            continue
        if state=='device':
            usb.append(serial)
        elif state=='unauthorized':
            unauthorized.append(serial)
    if len(usb)>1:
        return False,'Plusieurs téléphones USB détectés. Débranche les autres appareils.'
    if len(usb)==1:
        return True,'Téléphone autorisé en USB'
    if unauthorized:
        return False,'Déverrouille le téléphone et accepte « Autoriser le débogage USB ».'
    return False,'En attente du câble USB…'


class UsbMonitor(QObject):
    detected=Signal(bool,str)
    def __init__(self,parent=None,interval_ms=3200):
        super().__init__(parent)
        self._busy=False
        self._running=False
        self._timer=QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.check)
        self.detected.connect(self._mark_idle)

    def start(self):
        self._running=True
        self._timer.start()
        self.check()

    def stop(self):
        self._running=False
        self._timer.stop()

    def check(self):
        if self._busy or not self._running:
            return
        self._busy=True
        def probe():
            ready,message=usb_device_state()
            self.detected.emit(ready,message)
        threading.Thread(target=probe,name='camstudio-usb-probe',daemon=True).start()

    def _mark_idle(self,_ready,_message):
        self._busy=False
