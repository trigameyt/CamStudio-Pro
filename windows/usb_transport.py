"""ADB USB webcam transport for CamStudio Pro. Requires USB debugging authorization."""
import os
import re
import shutil
import subprocess
from pathlib import Path

PHONE_PORT = 8765

class UsbConnectionError(RuntimeError):
    pass

def find_adb():
    found=shutil.which("adb")
    if found:
        return str(Path(found))
    candidates=[]
    for env in ("ANDROID_HOME","ANDROID_SDK_ROOT"):
        if os.environ.get(env):
            candidates.append(Path(os.environ[env])/"platform-tools"/"adb.exe")
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"])/"Android"/"Sdk"/"platform-tools"/"adb.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise UsbConnectionError("ADB introuvable. Installe Android Platform Tools pour la connexion USB.")

def adb_run(adb, args, timeout=9):
    try:
        result=subprocess.run([str(adb),*args],text=True,capture_output=True,timeout=timeout,
                              creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    except subprocess.TimeoutExpired as e:
        raise UsbConnectionError("Le téléphone ne répond pas à ADB (délai dépassé).") from e
    except OSError as e:
        raise UsbConnectionError("ADB ne peut pas être lancé : "+str(e)) from e
    if result.returncode:
        message=(result.stderr or result.stdout or "Erreur inconnue ADB").strip()
        raise UsbConnectionError("Connexion USB impossible : "+message[:300])
    return result.stdout.strip()

class UsbTunnel:
    def __init__(self, adb, port):
        self.adb=adb
        self.port=int(port)
        self.url=f"http://127.0.0.1:{self.port}"
        self.closed=False

    def close(self):
        if self.closed:
            return
        self.closed=True
        try:
            adb_run(self.adb,["-d","forward","--remove",f"tcp:{self.port}"],timeout=3)
        except UsbConnectionError:
            pass

def open_usb_tunnel():
    adb=find_adb()
    # -d explicitly selects a physical USB device, never Wi-Fi debugging.
    device=adb_run(adb,["-d","get-state"])
    if device!="device":
        raise UsbConnectionError("Branche et autorise le Samsung dans la fenêtre « Débogage USB ».")
    port_text=adb_run(adb,["-d","forward","tcp:0",f"tcp:{PHONE_PORT}"])
    match=re.fullmatch(r"\d{1,5}",port_text)
    if not match or not 1024<=int(port_text)<=65535:
        raise UsbConnectionError("ADB n'a pas attribué de port local valide : "+port_text[:80])
    return UsbTunnel(adb,int(port_text))
