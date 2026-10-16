"""Verify audio page, features, sound backend and roadmap are removed."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from camstudio_v04.features import PAGES,PLANNED
from camstudio_v04.recordings import VideoViewer,scan_recordings
from app import Studio,STYLE
app=QApplication([])
app.setStyle('Fusion');app.setStyleSheet(STYLE)
root=Path(__file__).parent
names=[p.id for p in PAGES]
assert len(names)==8,names
assert 'audio' not in names
assert all('audio' not in x.lower() and 'micro' not in x.lower() for x in PLANNED)
ui_source=(root/'camstudio_v04'/'ui.py').read_text('utf-8').lower()
feat_source=(root/'camstudio_v04'/'features.py').read_text('utf-8').lower()
rec_source=(root/'camstudio_v04'/'recordings.py').read_text('utf-8').lower()
main_source=(root/'app.py').read_text('utf-8').lower()
scene_source=(root/'camstudio_v04'/'scene_editor.py').read_text('utf-8').lower()
for path,text in (('ui',ui_source),('features',feat_source),('main',main_source),('editor',scene_source)):
    assert 'audio' not in text and 'microphone' not in text,(path,'audio mention remains')
assert 'qaudiooutput' not in rec_source
assert 'setaudiooutput' not in rec_source
w=Studio();w._save_config=lambda:None;w._really_quit=True;w._tray_enabled=False
w.show();app.processEvents()
assert len(w._modern_ui.pages)==8
assert not hasattr(w._modern_ui,'_make_audio')
for p in PAGES:
    w._modern_ui.go(p.id)
    app.processEvents()
    assert w._modern_ui.stack.currentWidget() is w._modern_ui.pages[p.id]
print('NAVIGATION_EIGHT_PAGES_OK',flush=True)
video=next((x for x in scan_recordings() if x.kind=='video'),None)
if video:
    v=VideoViewer(video,w)
    v.show()
    for _ in range(20):app.processEvents()
    assert v.player is not None
    assert v.player.audioOutput() is None
    assert not hasattr(v,'audio')
    v.close()
    print('SILENT_MP4_PLAYER_OK',flush=True)
w.close()
print('V052_NO_AUDIO_TEST_OK',flush=True)
