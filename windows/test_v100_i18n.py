"""Validate V1 default English + eleven selectable languages, persistence, and UI binding."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,tempfile,json
from pathlib import Path
from PySide6.QtWidgets import QApplication,QLabel
from app import Studio,STYLE
from camstudio_v04.features import PAGES
from camstudio_v04.i18n import LANGUAGES,FR_EN,translate
from camstudio_v04.preferences import load_prefs,save_prefs

assert len(LANGUAGES)==12,LANGUAGES
assert len(set(code for code,_ in LANGUAGES))==12
assert LANGUAGES[0][0]=='en'
with tempfile.TemporaryDirectory() as tmp:
    os.environ['APPDATA']=tmp
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    w=Studio();w._save_config=lambda:None;w._really_quit=True;w._tray_enabled=False
    w.usb_monitor.stop()
    w.show();app.processEvents()
    ui=w._modern_ui
    assert ui.prefs['language']=='en'
    assert ui.language_combo.count()==12
    assert ui.buttons['home'].text().endswith('Home'),ui.buttons['home'].text()
    assert ui.buttons['settings'].text().endswith('Settings')
    assert 'Current mode' in ui.mode_label.text(),ui.mode_label.text()
    assert w.connection_method.itemText(1).startswith('USB (cable'),w.connection_method.itemText(1)
    print('DEFAULT_ENGLISH_UI_OK',flush=True)
    snapshot={}
    for code,_name in LANGUAGES:
        ui.set_language(code)
        app.processEvents()
        ui.go('settings')
        app.processEvents()
        assert ui.prefs['language']==code
        assert ui.language_combo.currentData()==code
        assert ui.buttons['settings'].text().strip()
        assert ui.mode_label.text().strip()
        assert ui.language_combo.count()==12
        snapshot[code]=ui.buttons['settings'].text()
    assert snapshot['en'].endswith('Settings'),snapshot
    assert snapshot['fr'].endswith('Paramètres'),snapshot
    assert snapshot['es'].endswith('Configuración'),snapshot
    assert snapshot['zh'].endswith('设置'),snapshot
    print('TWELVE_LANGUAGES_SWITCH_OK',ascii(snapshot),flush=True)
    # Don't translate camera output resolution data or user-entered credentials.
    assert w.output_modes.currentText() in w.output_modes.itemText(0)+w.output_modes.itemText(1)+w.output_modes.itemText(2)
    ui.set_language('ja')
    saved=load_prefs()
    assert saved['language']=='ja'
    print('LANGUAGE_PREF_PERSISTENCE_OK',flush=True)
    w.usb_monitor.stop();w.close()
    w2=Studio();w2._save_config=lambda:None;w2._really_quit=True;w2._tray_enabled=False;w2.usb_monitor.stop()
    assert w2._modern_ui.prefs['language']=='ja'
    assert w2._modern_ui.buttons['settings'].text().endswith('設定')
    print('LANGUAGE_REOPEN_PERSISTENCE_OK',flush=True)
    w2.close()
print('V1_I18N_TEST_OK')
