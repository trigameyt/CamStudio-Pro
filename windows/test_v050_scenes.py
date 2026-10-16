"""End-to-end beta scene tests; never write user's real profile or recordings."""
import os,sys,time,copy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
import numpy as np
from PySide6.QtCore import Qt,QPoint
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QInputDialog,QFileDialog,QMessageBox
from app import Studio,STYLE
from camstudio_v04.scene_engine import SceneStore,composite,process_with_scene

app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
with TemporaryDirectory() as tmp:
    w=Studio()
    w._save_config=lambda:None
    w._really_quit=True
    w._tray_enabled=False
    w.scenes=SceneStore(Path(tmp)/'scenes.json')
    w._modern_ui.scene_editor.store=w.scenes
    w._modern_ui.scene_editor.reload()
    w.show()
    u=w._modern_ui
    u.go('scenes')
    e=u.scene_editor
    for _ in range(10):
        app.processEvents()
    assert len(w.scenes.data['scenes'])==3
    assert e.choose.count()==3
    # Source is real processed video stream and output is composited.
    video=np.full((720,1280,3),(35,55,75),dtype=np.uint8)
    w.last_raw_frame=video
    natural=process_with_scene(video,w.settings,640,360,w.scenes.snapshot())
    assert natural.shape==(360,640,3)
    from processor import process_frame
    assert np.array_equal(natural,process_frame(video,w.settings,640,360))
    e.choose.setCurrentIndex(1)
    assert w.scenes.active()['id']=='title'
    layered=process_with_scene(video,w.settings,640,360,(w.scenes.active(),None,1.))
    changes=np.count_nonzero(layered!=natural)
    assert changes>100,changes
    print('COMPOSITOR_OUTPUT_TEST_OK',changes,flush=True)
    # New editor scene, new text, reorder and direct property changes.
    with patch.object(QInputDialog,'getText',return_value=('Stream public',True)):
        e.add_scene()
    assert w.scenes.active()['name']=='Stream public'
    with patch.object(QInputDialog,'getText',return_value=('Bonjour le stream',True)):
        e.add_text()
    assert e.active_layer()['text']=='Bonjour le stream'
    e.name_edit.setText('Bienvenue !')
    e.update_text()
    e.opacity.setValue(45)
    assert abs(e.active_layer()['opacity']-.45)<.001
    e.size_slider.setValue(76)
    assert e.active_layer()['font_size']==76
    e.background.setCurrentIndex(1)
    assert w.scenes.active()['background']=='color'
    # Image imported from temp location.
    photo=Path(tmp)/'logo.png'
    im=QImage(96,96,QImage.Format_ARGB32)
    im.fill(0xFF37A6E9)
    assert im.save(str(photo))
    with patch.object(QFileDialog,'getOpenFileName',return_value=(str(photo),'images')):
        e.add_image()
    assert e.active_layer()['kind']=='image'
    e.opacity.setValue(70)
    e.canvas.show()
    app.processEvents()
    idx_before=e.active_layer()['x']
    start=QPoint(round(idx_before*704+15),round(e.active_layer()['y']*396+12))
    QTest.mousePress(e.canvas,Qt.LeftButton,pos=start)
    QTest.mouseMove(e.canvas,QPoint(start.x()+75,start.y()+30),delay=25)
    QTest.mouseRelease(e.canvas,Qt.LeftButton,pos=QPoint(start.x()+75,start.y()+30))
    assert e.active_layer() is not None
    assert e.active_layer()['x']>idx_before+.08,(idx_before,e.active_layer()['x'])
    e.reorder_layer(-1)
    e.remove_layer()
    e.duplicate_scene()
    assert 'copie' in w.scenes.active()['name']
    e.transition.setCurrentText('Aucune')
    e.duration.setCurrentText('500 ms')
    assert w.scenes.data['transition']=='Aucune'
    assert w.scenes.data['transition_ms']==500
    # Persist real elements and independent selected scene.
    again=SceneStore(Path(tmp)/'scenes.json')
    assert again.active()['id']==w.scenes.active()['id']
    assert len(again.data['scenes'])==5
    print('SCENE_EDITOR_ADD_DRAG_SAVE_TEST_OK',flush=True)
    # Photo uses same overlays as video, only stored in temporary output.
    still=process_with_scene(video,w.settings,1280,720,w.scenes.snapshot())
    assert still.shape==(720,1280,3)
    # No scene leaked to user's actual config.
    assert (Path(tmp)/'scenes.json').is_file()
    w.close()
print('V050_SCENES_TESTS_OK',flush=True)
