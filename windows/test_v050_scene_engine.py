import os
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from PySide6.QtWidgets import QApplication
from camstudio_v04.scene_engine import SceneStore,composite

os.environ['QT_QPA_PLATFORM']='offscreen'
app=QApplication([])
frame=np.full((360,640,3),[10,20,30],dtype=np.uint8)
with TemporaryDirectory() as tmp:
 s=SceneStore(Path(tmp)/'scenes.json')
 a=composite(frame,s.snapshot())
 print('CAMERA_IDENTITY',np.array_equal(a,frame),'SHAPE',a.shape,flush=True)
 assert np.array_equal(a,frame)
 s.activate('title')
 b=composite(frame,(s.active(),None,1.))
 print('TITLE_CHANGED_PIXELS',np.count_nonzero(a!=b),flush=True)
 assert np.count_nonzero(a!=b)>100
 s.activate('standby')
 c=composite(frame,(s.active(),None,1.))
 print('STANDBY_CHANGED_PIXELS',np.count_nonzero(c!=frame),flush=True)
 assert np.count_nonzero(c!=frame)>20000
 s.save()
 d=SceneStore(Path(tmp)/'scenes.json')
 assert d.active()['id']=='standby'
 print('SCENE_ENGINE_OK',flush=True)
