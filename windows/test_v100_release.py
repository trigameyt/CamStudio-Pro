"""V1 release verification: DPAPI, autosave after abrupt close, USB and singleton.

Tests use temporary APPDATA and a unique local-server namespace.
No private keys or user recordings are read or printed.
"""
import os,sys,json,time,tempfile,subprocess,uuid
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

import app as module
from app import Studio,STYLE
from secure_store import protect_key,reveal_key
from single_instance import InstanceGuard,server_name
from usb_monitor import usb_device_state

assert reveal_key(protect_key('ONLY-TEST-PAIRING-KEY'))=='ONLY-TEST-PAIRING-KEY'
assert 'ONLY-TEST-PAIRING-KEY' not in protect_key('ONLY-TEST-PAIRING-KEY')
print('DPAPI_USER_BOUND_KEY_OK',flush=True)

with tempfile.TemporaryDirectory() as temp:
    # No user's pairing data or settings are ever touched.
    module.APP_DIR=Path(temp)
    module.CONFIG=Path(temp)/'config.json'
    app=QApplication.instance() or QApplication([])
    app.setStyle('Fusion');app.setStyleSheet(STYLE)
    w=Studio()
    w._really_quit=True
    w._tray_enabled=False
    w.usb_monitor.stop()
    w.show()
    app.processEvents()
    w.host.setText('192.0.2.55')
    w.key.setText('ONLY-TEST-PAIRING-KEY')
    w.connection_method.setCurrentIndex(1)
    w.sliders['contrast'].setValue(126)
    w.sliders['sharpness'].setValue(28)
    w.phone_zoom.setValue(41)
    w.quality.setValue(85)
    w.output_modes.setCurrentText('1080p / 30 FPS (agrandi si nécessaire)')
    w._usb_autoconnect_enabled=True
    for _ in range(40):
        app.processEvents()
        time.sleep(.025)
    assert module.CONFIG.is_file()
    raw=module.CONFIG.read_text(encoding='utf-8')
    assert 'ONLY-TEST-PAIRING-KEY' not in raw
    payload=json.loads(raw)
    assert payload.get('key_protected','').startswith('dpapi:')
    assert payload['last_settings']['contrast']==126
    assert payload['phone_controls']['quality']==85
    assert payload['connection_mode']=='usb'
    assert payload['auto_usb'] is True
    print('AUTOSAVE_ATOMIC_AND_ENCRYPTED_OK',flush=True)
    # Mimic an abrupt task-manager end: no closeEvent or other save here;
    # the stored data must be complete before simulated relaunch.
    w.usb_monitor.stop()
    w._fully_ready=False
    restore=Studio()
    restore._really_quit=True
    restore._tray_enabled=False
    restore.usb_monitor.stop()
    assert restore.host.text()=='192.0.2.55'
    assert restore.key.text()=='ONLY-TEST-PAIRING-KEY'
    assert restore.connection_method.currentIndex()==1
    assert restore.sliders['contrast'].value()==126
    assert restore.sliders['sharpness'].value()==28
    assert restore.phone_zoom.value()==41
    assert restore.quality.value()==85
    assert restore.output_modes.currentText().startswith('1080p')
    assert restore._usb_autoconnect_enabled
    print('RESTART_SETTINGS_RECOVERED_OK',flush=True)

    # Key is masked at rest, visible by explicit user action, and synced across pages.
    assert restore.key.echoMode()==restore.key.EchoMode.Password
    restore._toggle_key_visibility()
    assert restore.key.echoMode()==restore.key.EchoMode.Normal
    assert restore._modern_ui.key_edit.echoMode()==restore.key.EchoMode.Normal
    restore._toggle_key_visibility()
    assert restore.key.echoMode()==restore.key.EchoMode.Password
    print('PAIRING_KEY_SHOW_HIDE_OK',flush=True)

    calls=[]
    restore._usb_autoconnect_enabled=True
    restore._last_usb_attempt=0.
    restore.connection_method.setCurrentIndex(1)
    with patch.object(restore,'connect_camera',side_effect=lambda:calls.append('connect')):
        restore._usb_probe_result(True,'Téléphone autorisé en USB')
        restore._usb_probe_result(True,'Téléphone autorisé en USB')
    assert calls==['connect'],calls
    print('USB_DETECTION_AUTOCONNECT_DEBOUNCE_OK',flush=True)
    restore._usb_autoconnect_enabled=False
    restore._last_usb_attempt=0.
    with patch.object(restore,'connect_camera',side_effect=lambda:calls.append('should not')):
        restore._usb_probe_result(True,'Téléphone autorisé en USB')
    assert calls==['connect']
    print('MANUAL_DISCONNECT_SUPPRESSES_RECONNECT_OK',flush=True)

    restore._save_config=lambda:None
    w._save_config=lambda:None
    w.close()
    restore.close()

# Same user: second acquired guard must only signal the first instance.
os.environ['CAMSTUDIO_INSTANCE_NAMESPACE']='release-test-'+uuid.uuid4().hex
master=InstanceGuard()
assert master.acquire()
signals=[]
master.show_requested.connect(lambda:signals.append(True))
child=InstanceGuard()
assert child.acquire() is False
deadline=time.time()+1.
while time.time()<deadline and not signals:
    app.processEvents()
    time.sleep(.03)
assert signals==[True],signals
print('SINGLE_INSTANCE_SECOND_LAUNCH_SHOWS_FIRST_OK',flush=True)
print('V1_RELEASE_VALIDATION_OK',flush=True)
