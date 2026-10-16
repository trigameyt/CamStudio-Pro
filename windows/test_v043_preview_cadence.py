"""V0.4.3 preview cadence smoke test; no phone connection or config changes."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys,time
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap,QColor
from PySide6.QtWidgets import QApplication
from app import Studio,STYLE

app=QApplication(sys.argv);app.setStyle("Fusion");app.setStyleSheet(STYLE)
w=Studio()
w._save_config=lambda:None
w._really_quit=True
w._tray_enabled=False
w.show()
u=w._modern_ui
app.processEvents()
assert u.is_external_preview_visible() is True
assert u._preview_timer.interval()==40
key_sequences={"home":[],"studio":[],"hidden":[]}
phase=["home"]
step=[0]
def inject():
    step[0]+=1
    p=QPixmap(640,360)
    p.fill(QColor(step[0]%255,step[0]*17%255,step[0]*43%255))
    w.last_pixmap=p
def sample():
    label=u.home_preview if phase[0]!="studio" else u.studio_preview
    pix=label.pixmap()
    if pix and not pix.isNull():key_sequences[phase[0]].append(pix.cacheKey())
def switch_studio():
    phase[0]="studio"
    u.go("studio")
def switch_hidden():
    phase[0]="hidden"
    w.hide()
def done():
    def changes(xs):
        return sum(a!=b for a,b in zip(xs,xs[1:]))
    print("HOME_PREVIEW_CHANGES",changes(key_sequences["home"]),flush=True)
    print("STUDIO_PREVIEW_CHANGES",changes(key_sequences["studio"]),flush=True)
    print("HIDDEN_PREVIEW_CHANGES",changes(key_sequences["hidden"]),flush=True)
    assert changes(key_sequences["home"])>=16, "Home preview still stalled"
    assert changes(key_sequences["studio"])>=12, "Studio preview still stalled"
    assert changes(key_sequences["hidden"])==0, "Hidden window still repaints"
    w.close()
    app.quit()
generator=QTimer();generator.setInterval(36);generator.timeout.connect(inject)
observer=QTimer();observer.setInterval(18);observer.timeout.connect(sample)
generator.start();observer.start()
QTimer.singleShot(1250,switch_studio)
QTimer.singleShot(2250,switch_hidden)
QTimer.singleShot(2950,done)
app.exec()
print("V043_PREVIEW_25HZ_TEST_OK",flush=True)
