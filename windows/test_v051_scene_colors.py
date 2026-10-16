"""V0.5.1 color editing tests - use temp store, never edit real scene file."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication,QColorDialog

from app import Studio, STYLE
from camstudio_v04.scene_colors import SceneColorPicker,validate_color,PRESET_COLORS
from camstudio_v04.scene_engine import SceneStore,composite

app=QApplication(sys.argv)
app.setStyle('Fusion');app.setStyleSheet(STYLE)

assert validate_color(' #ff0030 ')=='#FF0030'
assert validate_color('invalid') is None
assert validate_color('#FF0') is None
assert validate_color('#GGGGGG') is None
picker=SceneColorPicker('Test','#123456')
changed=[]
picker.color_changed.connect(changed.append)
assert picker.color()=='#123456'
picker.hex.setText('#ab49e0')
picker.apply_hex()
assert picker.color()=='#AB49E0' and changed[-1]=='#AB49E0'
picker.hex.setText('#AAAAA')
picker.apply_hex()
assert picker.color()=='#AB49E0'
assert picker.hex.text()=='#AB49E0'
assert len(changed)==1
picker.preset_buttons[2].click()
assert picker.color()==PRESET_COLORS[2].upper()
with patch.object(QColorDialog,'getColor',return_value=QColor('#0055ee')):
    picker.custom.click()
    assert picker.color()=='#0055EE'
with patch.object(QColorDialog,'getColor',return_value=QColor()):
    picker.custom.click()
    assert picker.color()=='#0055EE'
print('COLOR_WIDGET_PRESETS_HEX_CUSTOM_CANCEL_OK',flush=True)

with TemporaryDirectory() as tmp:
    store=SceneStore(Path(tmp)/'scenes.json')
    w=Studio()
    w._save_config=lambda:None
    w._really_quit=True
    w._tray_enabled=False
    w.scenes=store
    e=w._modern_ui.scene_editor
    e.store=store
    e.reload()
    w.show()
    w._modern_ui.go('scenes')
    app.processEvents()

    # Camera scene: setting bg color enables opaque color mode and emits save.
    assert store.active()['id']=='camera'
    assert store.active()['background']=='camera'
    e.background_color.set_color('#32AABB')
    assert store.active()['background']=='color'
    assert e.background.currentIndex()==1
    assert store.active()['background_color']=='#32AABB'
    assert e.background_color.color()=='#32AABB'
    assert not e.text_color.isVisible(), 'Text picker should not appear without text'
    frame=np.zeros((360,640,3),dtype=np.uint8)
    bgr=composite(frame,(store.active(),None,1.))
    assert np.all(bgr[320,500]==(187,170,50)),bgr[320,500]
    assert np.all(bgr[320,500]!=frame[320,500])
    print('BACKGROUND_COLOR_RGB_PIXELS_OK',bgr[320,500].tolist(),flush=True)

    # Selected text, text color stored per-layer and distinct from background.
    e.choose.setCurrentIndex(e.choose.findData('title'))
    assert store.active()['id']=='title'
    e.select_layer('title-line')
    assert e.text_color.isVisible()
    e.text_color.hex.setText('#FF3366')
    e.text_color.apply_hex()
    assert e.active_layer()['color']=='#FF3366'
    assert store.active()['background']=='camera'
    assert e.background_color.color()=='#101321'
    old=store.active()['layers'][0]['color']
    e.text_color.preset_buttons[5].click()
    assert e.active_layer()['color']==PRESET_COLORS[5].upper()
    assert old != e.active_layer()['color']
    print('INDIVIDUAL_TEXT_COLOR_OK',flush=True)

    # Return to edited camera scene: its independent background must persist.
    e.choose.setCurrentIndex(e.choose.findData('camera'))
    assert e.background_color.color()=='#32AABB'
    assert store.active()['background']=='color'
    e.background.setCurrentIndex(0)
    assert store.active()['background']=='camera'
    e.background_color.preset_buttons[4].click()
    assert store.active()['background']=='color'
    assert store.active()['background_color']==PRESET_COLORS[4].upper()

    # Verify storage after reopening separately, no user's profile touched.
    copy_store=SceneStore(Path(tmp)/'scenes.json')
    assert copy_store.get('camera')['background_color']==PRESET_COLORS[4].upper()
    assert copy_store.get('title')['layers'][0]['color']==PRESET_COLORS[5].upper()
    assert copy_store.get('title')['background']=='camera'
    print('PER_SCENE_COLOR_PERSISTENCE_OK',flush=True)
    w.close()
print('V051_SCENE_COLOR_TESTS_OK',flush=True)
