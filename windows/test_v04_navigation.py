import os,sys,hashlib
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication,QLineEdit
from PySide6.QtCore import Qt
from app import Studio,STYLE
from camstudio_v04.features import PAGES
app=QApplication(sys.argv)
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
w=Studio()
w._save_config=lambda:None  # test must never replace actual Wi-Fi pairing
w.show()
app.processEvents()
ui=w._modern_ui
print('V04_LOADED',len(ui.pages),ui.prefs['advanced_mode'],flush=True)
assert len(ui.pages)==8
assert 'audio' not in ui.pages
assert set(ui.pages)=={p.id for p in PAGES}
for p in PAGES:
    ui.go(p.id)
    app.processEvents()
    print('PAGE_OK',p.id,'VISIBLE',ui.stack.currentWidget() is ui.pages[p.id],flush=True)
    assert ui.stack.currentWidget() is ui.pages[p.id]
ui.go('settings')
ui.set_advanced(True)
assert ui.original_controls.isVisible()==False or ui.original_controls.isVisible()==True
assert ui.prefs['advanced_mode']
ui.go('camera')
assert not ui.original_controls.isHidden()
ui.go('connections')
ui.host_edit.setText('192.0.2.10')
assert w.host.text()=='192.0.2.10'
ui.key_edit.setText('ONLY-TEST-KEY')
assert w.key.text()=='ONLY-TEST-KEY'
print('SIMPLE_ADVANCED_SYNC_OK',flush=True)
ui.set_advanced(False)
ui.go('camera')
assert ui.original_controls.isHidden()
ui.go('connections')
assert ui.host_edit.isVisible()
print('SIMPLE_MODE_CONNECTION_OK',flush=True)
w._really_quit=True
w.close()
print('V04_NAVIGATION_OK',flush=True)
