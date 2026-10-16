"""Verify scene content flows through Windows output thread to both webcam and video."""
import os,sys,time
from tempfile import TemporaryDirectory
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
import numpy as np
from PySide6.QtWidgets import QApplication
from app import Studio,STYLE
from camstudio_v04.scene_engine import SceneStore
app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
class Capture:
 def __init__(self):self.frames=[]
 def send(self,frame):self.frames.append(frame.copy())
 def close(self):pass
w=Studio();w._save_config=lambda:None
w._really_quit=True;w._tray_enabled=False
w.show();app.processEvents()
with TemporaryDirectory() as temp:
 w.scenes=SceneStore(Path(temp)/'scenes.json')
 w.out_width=1280;w.out_height=720
 w._modern_ui.scene_editor.store=w.scenes
 w._modern_ui.scene_editor.reload()
 video=np.ones((720,1280,3),dtype=np.uint8)*52
 cam=Capture()
 w.vcam=cam
 w.scenes.activate('title')
 w.scenes._from=None
 w._render_frame(video,draw_preview=False)
 deadline=time.time()+5
 while not cam.frames and time.time()<deadline:
  w._drain_output();app.processEvents();time.sleep(.02)
 assert cam.frames and cam.frames[0].shape==(720,1280,3)
 output=cam.frames[0]
 print('FIRST_SCENE_PIXEL_VARIETY',len(np.unique(output.reshape(-1,3),axis=0)),flush=True)
 assert len(np.unique(output.reshape(-1,3),axis=0))>=2
 w.scenes.data['transition']='Aucune'
 w.scenes.activate('standby')
 w._render_frame(video,draw_preview=False)
 deadline=time.time()+5
 while len(cam.frames)<2 and time.time()<deadline:
  w._drain_output();app.processEvents();time.sleep(.02)
 assert len(cam.frames)==2
 a,b=cam.frames[:2]
 delta=np.mean(np.abs(a.astype(np.float32)-b.astype(np.float32)))
 print('SCENE_SWITCH_PIXELS_AVG_DIFF',round(float(delta),2),flush=True)
 assert delta>10
 print('REAL_OUTPUT_PROCESSING_OK',flush=True)
 w.vcam=None
w.close()
