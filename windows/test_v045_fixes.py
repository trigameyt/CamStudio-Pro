"""CamStudio Pro v0.4.5 UI+recording regressions, without touching existing media."""
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import Future
import os,sys,time
os.environ['QT_QPA_PLATFORM']='offscreen'
import cv2
import numpy as np
from PySide6.QtWidgets import QApplication,QPushButton,QStyle
from PySide6.QtCore import Qt,QPoint,QPointF
from PySide6.QtTest import QTest
from PySide6.QtGui import QMouseEvent
from app import Studio,STYLE,WheelSafeSlider
from camstudio_v04.controls import VideoSeekSlider
from camstudio_v04.recordings import RecordingGallery,Recording,VideoViewer,_thumbnail

app=QApplication(sys.argv);app.setStyle("Fusion");app.setStyleSheet(STYLE)
w=Studio();w._save_config=lambda:None;w._really_quit=True;w._tray_enabled=False
w.show();app.processEvents()
sliders=[w.phone_zoom,w.quality,w.phone_exposure,w.phone_fps,*w.sliders.values()]
for slider in sliders:
    slider.resize(290,30);slider.setValue(slider.minimum())
    app.processEvents()
    QTest.mouseClick(slider,Qt.LeftButton,pos=QPoint(int(slider.width()*.74),slider.height()//2))
    assert slider.value()>slider.minimum(),(slider.minimum(),slider.maximum(),slider.value())
print('TEN_SLIDERS_CLICKABLE',len(sliders),flush=True)
slider=sliders[0]
QTest.mousePress(slider,Qt.LeftButton,pos=QPoint(18,slider.height()//2))
QTest.mouseMove(slider,QPoint(240,slider.height()//2),delay=15)
QTest.mouseRelease(slider,Qt.LeftButton,pos=QPoint(240,slider.height()//2))
assert slider.value()>slider.minimum()
print('DRAG_GESTURE_OK',flush=True)
seek=VideoSeekSlider(Qt.Horizontal)
seek.setRange(0,30000);seek.resize(400,28);seek.show();app.processEvents()
positions=[];seek.sliderMoved.connect(positions.append)
QTest.mouseClick(seek,Qt.LeftButton,pos=QPoint(200,14))
assert 13000<=seek.value()<=17000,seek.value()
assert positions and positions[-1]==seek.value()
print('SEEK_CLICK_MIDPOINT_MS',seek.value(),flush=True)
w._modern_ui.go('record');g=w._modern_ui.gallery;app.processEvents()
assert len(g._all)>=4
seen=[]
g.open_item=lambda f:seen.append(f)
for _ in range(40):
    app.processEvents();time.sleep(.015)
tile=g.grid.itemAt(0).widget()
thumb=tile.findChildren(QPushButton)[0]
assert 'Lire' in thumb.accessibleName() or 'Voir' in thumb.accessibleName()
QTest.mouseClick(thumb,Qt.LeftButton)
assert len(seen)==1
assert isinstance(thumb.icon().isNull(),bool) and not thumb.icon().isNull()
print('THUMBNAIL_DIRECT_OPEN_OK',flush=True)
combo=g.filter
assert combo.currentIndex()==0
combo.setCurrentIndex(1);app.processEvents()
assert g.grid.count()==sum(x.kind=='video' for x in g._all)
combo.setCurrentIndex(2);app.processEvents()
assert g.grid.count()==sum(x.kind=='photo' for x in g._all)
print('COMBO_FILTER_OK',flush=True)
# Real MP4 writer: pause cannot split files; resumes into same container.
with TemporaryDirectory() as tmp:
    path=Path(tmp)/'test_pause.mp4'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),30,(320,240))
    assert writer.isOpened()
    w.writer=writer
    w.record_path=path
    w.out_width=320;w.out_height=240
    w.record_paused=False
    def deliver(value):
        fut=Future()
        fut.set_result(np.full((240,320,3),value,dtype=np.uint8))
        w._output_future=fut
        w._drain_output()
    for i in range(8):deliver(30+i)
    w.pause_record()
    assert w.record_paused
    assert any(word in w.pause_btn.text() for word in ('Resume','Reprendre'))
    assert w._modern_ui.gallery._exclusion()==path
    for i in range(30):deliver(100+i)
    assert w.record_paused
    w.pause_record()
    assert not w.record_paused
    for i in range(7):deliver(190+i)
    w.toggle_record()
    assert not w.record_paused and w.writer is None
    cap=cv2.VideoCapture(str(path))
    frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps=cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    print('RECORD_SINGLE_FILE',path.exists(),'FRAMES',frames,'FPS',fps,flush=True)
    assert frames==15,frames
    assert path.stat().st_size>500
print('V045_FIVE_FIXES_TEST_OK',flush=True)
w.close()
