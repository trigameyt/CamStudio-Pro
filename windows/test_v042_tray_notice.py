"""Tray notice test with mocked dialogs; never writes user's camera secrets."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox,QCheckBox
from app import Studio,STYLE
app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
w=Studio()
w._save_config=lambda:None
w.config.pop('tray_notice_seen',None)
w._tray_enabled=True
w.show()
with patch.object(QMessageBox,'exec',return_value=0) as dialog:
    w.close()
    assert not w.isVisible()
    assert w.config.get('tray_notice_seen') is True
    w.show()
    w.close()
    assert dialog.call_count==1,dialog.call_count
    print('TRAY_FIRST_CLOSE_ONE_NOTICE_OK',flush=True)
# Unchecked: dialog should repeat until user opts out.
w.config['tray_notice_seen']=False
with patch.object(QMessageBox,'exec',return_value=0) as dialog, patch.object(QCheckBox,'isChecked',return_value=False):
    w.show()
    w.close()
    w.show()
    w.close()
    assert dialog.call_count==2,dialog.call_count
    assert not w.config['tray_notice_seen']
    print('TRAY_UNCHECKED_REPEATS_OK',flush=True)
w._really_quit=True
w.close()
print('TRAY_V042_SMOKE_OK',flush=True)
