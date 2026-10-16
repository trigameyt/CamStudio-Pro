"""CamStudio Pro V1.0 - Windows receiver, scenes, capture and virtual webcam."""
from __future__ import annotations
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import cv2
import numpy as np
import requests
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPixmap, QIcon, QPainter, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QLineEdit, QSlider, QComboBox,
    QCheckBox, QScrollArea, QMessageBox, QInputDialog, QGridLayout,
    QSizePolicy, QSystemTrayIcon, QMenu,
)

from processor import ImageSettings, PRESETS, process_frame, viewport, rotated_dimensions, output_content_bounds, source_point_from_output
from stream import MJPEGReader
from usb_transport import open_usb_tunnel, UsbConnectionError
from usb_monitor import UsbMonitor
from secure_store import protect_key, reveal_key
from single_instance import InstanceGuard
from camstudio_v04.controls import ClickJumpSlider
from camstudio_v04.scene_engine import SceneStore, process_with_scene

APP_DIR = Path(os.getenv('APPDATA', str(Path.home()))) / 'CamStudioPro'
CONFIG = APP_DIR / 'config.json'
OUTPUT_W, OUTPUT_H, OUTPUT_FPS = 1280, 720, 30
VIDEO_MODES = {
    '720p / 30 FPS': (1280, 720, 30),
    '1080p / 30 FPS (agrandi si nécessaire)': (1920, 1080, 30),
    '1440p / 60 FPS (agrandi si nécessaire)': (2560, 1440, 60),
}

STYLE = """
QWidget { background-color: #10131d; color: #e8ebfa; font-family: 'Segoe UI'; font-size: 12px; }
QLabel#Brand { color: #f3f2ff; font-size: 22px; font-weight: 800; }
QLabel#Subheading { color: #979fb6; font-size: 11px; }
QLabel#Title { color: #fafaff; font-size: 23px; font-weight: 700; }
QLabel#Section { color: #f4f3ff; font-size: 14px; font-weight: 700; padding-top: 12px; }
QLabel#Tiny { color: #9ca3ba; font-size: 11px; }
QLabel#Status { color: #aab0c8; font-weight: 600; }
QFrame#Sidebar { background: #171a28; border-right: 1px solid #292d42; }
QFrame#Panel { background: #181b29; border: 1px solid #303348; border-radius: 12px; }
QFrame#Preview { background: #080a10; border: 1px solid #36384f; border-radius: 16px; }
QLineEdit, QComboBox { background: #222639; border: 1px solid #3a3e56; border-radius: 7px; min-height: 32px; padding: 3px 9px; selection-background-color: #8f71ff; }
QLineEdit:focus, QComboBox:focus { border-color: #9779ff; }
QPushButton { background: #2b2f43; border: 1px solid #42465f; padding: 8px 12px; border-radius: 8px; font-weight: 600; }
QPushButton:hover { background: #373b54; }
QPushButton:pressed { background: #525875; }
QPushButton#Accent { background: #845cf7; border-color: #9776fa; color: white; }
QPushButton#Accent:hover { background: #9877ff; }
QPushButton#Danger { background: #6c3145; border-color: #9a4858; }
QPushButton#Dark { background: #1c1e2d; border-color: #34384f; }
QSlider::groove:horizontal { height: 5px; background: #34374d; border-radius: 2px; }
QSlider::handle:horizontal { background: #9f7cff; border-radius: 7px; width: 15px; margin: -5px 0; }
QSlider::sub-page:horizontal { background: #8765ee; border-radius: 3px; }
QCheckBox { spacing: 9px; }
QScrollArea { border: 0px; background: transparent; }
"""


def _scroll_settings_panel(widget, event):
    # Always move the right-hand scrollbar, never change settings on hover.
    parent = widget.parentWidget()
    while parent is not None and not isinstance(parent, QScrollArea):
        parent = parent.parentWidget()
    if parent is None:
        event.ignore()
        return
    scroll = parent.verticalScrollBar()
    pixels = event.pixelDelta().y()
    if pixels:
        delta = pixels
    else:
        delta = event.angleDelta().y() / 120.0 * max(42, scroll.singleStep()*3)
    scroll.setValue(scroll.value() - int(round(delta)))
    event.accept()


class WheelSafeSlider(ClickJumpSlider):
    def wheelEvent(self,event):
        _scroll_settings_panel(self,event)


class WheelSafeComboBox(QComboBox):
    def wheelEvent(self,event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            _scroll_settings_panel(self,event)


class InteractivePreview(QLabel):
    """Click-to-center, drag-to-pan and wheel-to-zoom on the displayed video."""
    point_clicked = Signal(float, float)
    pan_dragged = Signal(float, float)
    wheel_zoom = Signal(int, float, float)

    def __init__(self, text):
        super().__init__(text)
        self.setCursor(Qt.CrossCursor)
        self._prev = None
        self._start = None
        self._dragged = False
        self.setToolTip('Molette : zoomer sur le pointeur  •  Clic : centrer  •  Glisser : déplacer')

    def _normalized(self, pos):
        px = self.pixmap()
        if px is None or px.isNull():
            return None
        w, h = px.width(), px.height()
        left, top = (self.width()-w)/2, (self.height()-h)/2
        if not (left <= pos.x() <= left+w and top <= pos.y() <= top+h):
            return None
        return (min(1.,max(0.,(pos.x()-left)/w)), min(1.,max(0.,(pos.y()-top)/h)))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._start = e.position()
            self._prev = e.position()
            self._dragged = False
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._prev is not None and (e.buttons() & Qt.LeftButton):
            a = self._normalized(self._prev)
            b = self._normalized(e.position())
            if a is not None and b is not None:
                if abs(a[0]-b[0])+abs(a[1]-b[1]) > 0.003:
                    self.pan_dragged.emit(b[0]-a[0], b[1]-a[1])
                    self._dragged = True
            self._prev = e.position()
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._prev is not None:
            point = self._normalized(e.position())
            if point is not None and not self._dragged:
                self.point_clicked.emit(*point)
            self._prev = None
            self._start = None
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def wheelEvent(self, e):
        xy = self._normalized(e.position())
        if xy is not None:
            self.wheel_zoom.emit(1 if e.angleDelta().y() > 0 else -1, *xy)
            e.accept()
            return
        super().wheelEvent(e)


class Studio(QMainWindow):
    battery_received = Signal(object)
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CamStudio Pro | Studio caméra')
        self.resize(1480, 870)
        self.setMinimumSize(940, 670)
        self.worker = None
        self.usb_tunnel = None
        self._active_base_url = None
        self.retired_workers = []
        self.settings = ImageSettings()
        self.scenes = SceneStore()
        self.out_width, self.out_height, self.out_fps = OUTPUT_W, OUTPUT_H, OUTPUT_FPS
        self.last_raw_frame = None
        self._last_output_delivery = 0.0
        self._output_pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix="camstudio-output")
        self._output_future = None
        self._preview_width, self._preview_height = 800, 450
        self._last_preview_at = 0.
        self._last_camera_ui_update_at = 0.
        self._last_actual_receive_fps = 0.
        self._output_sent_count = 0
        self._last_actual_output_fps = 0.
        self.battery_received.connect(self._display_battery)
        self._clock_ticks = 0
        self._battery_polling = False
        self.last_pixmap = None
        self.vcam = None
        self.writer = None
        self.record_paused = False
        self.record_path = None
        self.frame_count = 0
        self.fps_t = time.monotonic()
        self.fps_count = 0
        self.last_remote_error = ''
        self.config = self._load_config()
        self._usb_autoconnect_enabled=bool(self.config.get('auto_usb',True))
        self._last_usb_attempt=0.
        self._last_usb_state=None
        self._really_quit = False
        self._tray_notified = False
        self._build()
        # CAMSTUDIO_V04_UI_HOOK
        from camstudio_v04.ui import mount_v04
        mount_v04(self)
        self._apply_saved()
        self._setup_tray()
        self._autosave_timer=QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(350)
        self._autosave_timer.timeout.connect(self._save_config)
        for edit in (self.host,self.key):
            edit.textChanged.connect(self._schedule_save)
        self.output_modes.currentTextChanged.connect(self._schedule_save)
        self.rotation.currentIndexChanged.connect(self._schedule_save)
        self.fit_combo.currentIndexChanged.connect(self._schedule_save)
        for slider in (*self.sliders.values(),self.phone_zoom,self.quality,self.phone_exposure,self.phone_fps):
            slider.valueChanged.connect(self._schedule_save)
        for cb in self.flags.values():
            cb.toggled.connect(self._schedule_save)
        self.usb_monitor=UsbMonitor(self)
        self.usb_monitor.detected.connect(self._usb_probe_result)
        self._fully_ready=True
        self.usb_monitor.start()
        self.status('Prêt — connecte ton application Android CamStudio Pro', '#b1b6cd')
        self.clock = QTimer(self)
        self.clock.timeout.connect(self._tick)
        self.clock.start(1000)
        self.frame_timer = QTimer(self)
        # USB / MJPEG can supply 24-30 frames/sec. 55ms capped us at ~18 FPS.
        # 15ms only checks the latest buffer; expensive preview is throttled below.
        self.frame_timer.setInterval(15)
        self.frame_timer.timeout.connect(self._poll_latest_frame)
        self.frame_timer.start()


    def _setup_tray(self):
        icon = QPixmap(64, 64)
        icon.fill(Qt.transparent)
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor('#845cf7'))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(2, 2, 60, 60, 16, 16)
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(41)
        painter.setFont(font)
        painter.drawText(icon.rect(), Qt.AlignCenter, 'C')
        painter.end()
        self.setWindowIcon(QIcon(icon))
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self._tray_enabled = QSystemTrayIcon.isSystemTrayAvailable()
        if not self._tray_enabled:
            return
        menu = QMenu()
        show_action = QAction('Afficher CamStudio Pro', self)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)
        menu.addSeparator()
        exit_action = QAction('Quitter CamStudio Pro', self)
        exit_action.triggered.connect(self._quit_from_tray)
        menu.addAction(exit_action)
        self.tray.setToolTip('CamStudio Pro - webcam en arrière-plan')
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self):
        self._really_quit = True
        self.close()
        QApplication.instance().quit()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange and self.isMinimized() and getattr(self,'_tray_enabled',False):
            QTimer.singleShot(0,self.hide)

    def _load_config(self):
        try:
            result=json.loads(CONFIG.read_text('utf-8'))
            if not isinstance(result,dict):
                raise ValueError('Invalid configuration')
        except (OSError,ValueError):
            result={'profiles':{name:vars(value).copy() for name,value in PRESETS.items()}}
        encrypted=result.get('key_protected','')
        if encrypted:
            try:
                result['key']=reveal_key(encrypted)
            except (OSError,ValueError):
                # Do not overwrite an undecryptable key without user action.
                result['key']=''
                result['_key_unreadable']=True
        return result

    def _schedule_save(self,*_args):
        if getattr(self,'_fully_ready',False) and hasattr(self,'_autosave_timer'):
            self._autosave_timer.start()

    def _save_config(self):
        # Atomic replacement prevents truncation even if Windows ends the task
        # during a save; changes are also persisted on a short debounce timer.
        APP_DIR.mkdir(parents=True,exist_ok=True)
        self.config['host']=self.host.text()
        self.config['key']=self.key.text()
        self.config['last_settings']=vars(self.settings).copy()
        self.config['output_mode']=self.output_modes.currentText()
        self.config['connection_mode']='usb' if self.connection_method.currentIndex()==1 else 'wifi'
        self.config['auto_usb']=self._usb_autoconnect_enabled
        self.config['phone_controls']={
            'zoom':self.phone_zoom.value(),
            'quality':self.quality.value(),
            'exposure':self.phone_exposure.value(),
            'fps':self.phone_fps.value(),
        }
        serialized=self.config.copy()
        token=self.key.text().strip()
        if token:
            serialized['key_protected']=protect_key(token)
            serialized.pop('_key_unreadable',None)
        elif not self.config.get('_key_unreadable'):
            serialized.pop('key_protected',None)
        # Never save the plaintext key to disk.
        serialized.pop('key',None)
        serialized.pop('_key_unreadable',None)
        staging=CONFIG.with_name('config.json.tmp')
        staging.write_text(json.dumps(serialized,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        os.replace(staging,CONFIG)

    def _toggle_key_visibility(self):
        shown=self.key.echoMode()==QLineEdit.Password
        mode=QLineEdit.Normal if shown else QLineEdit.Password
        self.key.setEchoMode(mode)
        if hasattr(self,'key_show_btn'):
            self.key_show_btn.setText('Masquer la clé' if shown else 'Afficher la clé')
        modern=getattr(self,'_modern_ui',None)
        if modern and hasattr(modern,'key_edit'):
            modern.key_edit.setEchoMode(mode)
            if hasattr(modern,'key_show_btn'):
                modern.key_show_btn.setText('Masquer la clé' if shown else 'Afficher la clé')

    def _usb_probe_result(self,ready,message):
        if not self._usb_autoconnect_enabled:
            return
        if self.worker is not None or not ready:
            if message!=self._last_usb_state:
                self._last_usb_state=message
                if self.worker is None and self.connection_method.currentIndex()==1:
                    self.status(message)
            return
        if not self.key.text().strip():
            if self._last_usb_state!='key_required':
                self._last_usb_state='key_required'
                self.status('USB détecté : saisis une fois la clé affichée sur Android.')
            return
        now=time.monotonic()
        if now-self._last_usb_attempt < 8.:
            return
        self._last_usb_attempt=now
        # USB takes priority if phone is connected, unless the user explicitly
        # selected Wi-Fi during this session.
        if self.connection_method.currentIndex()!=1:
            self.connection_method.blockSignals(True)
            self.connection_method.setCurrentIndex(1)
            self.connection_method.blockSignals(False)
            self._on_connection_method_changed(1)
        self.status('Téléphone USB détecté : connexion automatique…')
        self.connect_camera()

    def _card(self, parent=None):
        w = QFrame(parent)
        w.setObjectName('Panel')
        return w

    def _label(self, text, object_name=None):
        l = QLabel(text)
        if len(text)>49: l.setWordWrap(True)
        if object_name: l.setObjectName(object_name)
        return l

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        hbox = QHBoxLayout(root)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName('Sidebar')
        sidebar.setFixedWidth(216)
        left = QVBoxLayout(sidebar)
        left.setContentsMargins(20, 26, 20, 24)
        left.setSpacing(13)
        left.addWidget(self._label('◉  CAMSTUDIO', 'Brand'))
        left.addWidget(self._label('PRO   /   VERSION 0.3.1', 'Subheading'))
        left.addSpacing(30)
        for text, subtitle in [('◉   Caméra', 'Flux en direct'), ('◈   Studio', 'Réglages image'), ('▣   Profils', 'Scènes personnalisées'), ('◉   Sortie webcam', 'OBS / Discord')]:
            nav = self._card()
            nv = QVBoxLayout(nav)
            nv.setContentsMargins(12, 10, 12, 10)
            nv.addWidget(QLabel(text))
            nv.addWidget(self._label(subtitle, 'Tiny'))
            left.addWidget(nav)
        left.addStretch()
        left.addWidget(self._label('Diffusion locale uniquement', 'Tiny'))
        left.addWidget(self._label('Vidéo non envoyée au cloud', 'Tiny'))
        hbox.addWidget(sidebar)

        content = QWidget()
        center = QVBoxLayout(content)
        center.setContentsMargins(24, 22, 24, 20)
        center.setSpacing(14)
        header = QHBoxLayout()
        head_text = QVBoxLayout()
        head_text.addWidget(self._label('Studio caméra', 'Title'))
        head_text.addWidget(self._label('Contrôle vidéo • correction d’image • capture • webcam virtuelle', 'Subheading'))
        header.addLayout(head_text)
        header.addStretch()
        self.connection_indicator = self._label('● HORS LIGNE', 'Status')
        header.addWidget(self.connection_indicator)
        self.battery_label = self._label('🔋 Batterie : -- %', 'Status')
        header.addSpacing(16)
        header.addWidget(self.battery_label)
        center.addLayout(header)
        preview = QFrame()
        preview.setObjectName('Preview')
        pv = QVBoxLayout(preview)
        pv.setContentsMargins(10,10,10,10)
        self.image = InteractivePreview('CAMSTUDIO PRO\n\nAucune caméra connectée')
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setStyleSheet('color:#777e99; font-size:20px; font-weight:600; background:transparent;')
        self.image.setMinimumSize(340,250)
        self.image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pv.addWidget(self.image, 1)
        self.image.point_clicked.connect(self._point_clicked)
        self.image.pan_dragged.connect(self._pan_dragged)
        self.image.wheel_zoom.connect(self._wheel_zoom)
        center.addWidget(preview, 1)
        bottom = self._card()
        toolbar = QHBoxLayout(bottom)
        toolbar.setContentsMargins(16,13,16,13)
        self.capture_btn = self._button('▧  Capture photo', self.capture)
        self.rec_btn = self._button('●  Enregistrer', self.toggle_record)
        self.pause_btn = self._button('⏸  Pause', self.pause_record)
        self.pause_btn.setEnabled(False)
        self.virtual_btn = self._button('◉  Activer webcam virtuelle', self.toggle_virtual, accent=True)
        toolbar.addWidget(self.capture_btn)
        toolbar.addWidget(self.rec_btn)
        toolbar.addWidget(self.pause_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.virtual_btn)
        center.addWidget(bottom)
        self.status_text = self._label('Initialisation...', 'Status')
        center.addWidget(self.status_text)
        hbox.addWidget(content, 1)

        right_scroll = QScrollArea()
        right_scroll.setFixedWidth(338)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidgetResizable(True)
        controls = QWidget()
        controls_l = QVBoxLayout(controls)
        controls_l.setContentsMargins(11,18,14,18)
        controls_l.setSpacing(9)
        controls_l.addWidget(self._label('Connexion du téléphone', 'Section'))
        controls_l.addWidget(self._label('Mode de connexion', 'Tiny'))
        self.connection_method = WheelSafeComboBox()
        self.connection_method.addItems(['Wi-Fi', 'USB (câble + débogage USB)'])
        self.connection_method.currentIndexChanged.connect(self._on_connection_method_changed)
        controls_l.addWidget(self.connection_method)
        controls_l.addWidget(self._label('Adresse IP du téléphone (mode Wi-Fi)', 'Tiny'))
        self.host = QLineEdit()
        self.host.setPlaceholderText('192.168.1.50')
        controls_l.addWidget(self.host)
        controls_l.addWidget(self._label('Clé affichée dans l’application Android', 'Tiny'))
        self.key = QLineEdit()
        self.key.setPlaceholderText('Clé de connexion')
        self.key.setEchoMode(QLineEdit.Password)
        controls_l.addWidget(self.key)
        keyrow=QHBoxLayout()
        self.key_show_btn=self._button('Afficher la clé',self._toggle_key_visibility)
        keyrow.addWidget(self.key_show_btn)
        keyrow.addStretch()
        controls_l.addLayout(keyrow)
        buttons = QHBoxLayout()
        self.connect_btn = self._button('Connecter', self.connect_camera, accent=True)
        self.disconnect_btn = self._button('Déconnecter', self.disconnect_camera)
        buttons.addWidget(self.connect_btn); buttons.addWidget(self.disconnect_btn)
        controls_l.addLayout(buttons)
        self.usb_quality_btn = self._button('Qualité USB élevée : 1080p / JPEG 90', self._enable_usb_quality)
        controls_l.addWidget(self.usb_quality_btn)
        controls_l.addWidget(self._label('USB via ADB : liaison locale plus stable. La résolution native et les FPS restent limités par le Samsung.', 'Tiny'))
        controls_l.addWidget(self._label('Contrôles de la caméra', 'Section'))
        row = QHBoxLayout()
        row.addWidget(self._button('⟳ Changer caméra', lambda: self.remote('switch', '1')))
        self.torch_btn = self._button('☼ Lampe OFF', self.toggle_torch)
        row.addWidget(self.torch_btn)
        controls_l.addLayout(row)
        self.phone_zoom = self._range(controls_l, 'Zoom optique / numérique téléphone', 0, 100, 0, lambda v:self.remote('zoom',str(v)), remote=True)
        self.quality = self._range(controls_l, 'Qualité JPEG réseau', 40, 95, 75, lambda v:self.remote('quality',str(v)), remote=True)
        self.phone_exposure = self._range(controls_l, 'Exposition matérielle téléphone', 0, 100, 50, lambda v:self.remote('exposure',str(v)), remote=True)
        self.phone_fps = self._range(controls_l, 'Limite FPS réseau', 5, 30, 25, lambda v:self.remote('fps',str(v)), remote=True)
        controls_l.addWidget(self._label('Réglages de l’image', 'Section'))
        self.sliders = {}
        for attr, label, a, b, d in (
            ('brightness', 'Luminosité',-100,100,0),
            ('contrast','Contraste',0,200,100),
            ('saturation','Saturation',0,200,100),
            ('sharpness','Netteté',0,100,0),
            ('warmth','Température',-80,80,0),
            ('zoom','Recadrage / Zoom',100,600,100),
        ):
            self.sliders[attr] = self._range(controls_l,label,a,b,d,lambda v, k=attr: self._set(k,v))
        orient = QHBoxLayout()
        orient.addWidget(self._label('Rotation'))
        self.rotation = WheelSafeComboBox()
        self.rotation.addItems(['0°','90°','180°','270°'])
        self.rotation.currentIndexChanged.connect(lambda i:self._set('rotation',i*90))
        orient.addWidget(self.rotation)
        controls_l.addLayout(orient)
        controls_l.addWidget(self._label('Cadrage et proportions', 'Section'))
        self.fit_combo = WheelSafeComboBox()
        self.fit_combo.addItems(['Contenir : image entière (bandes)', 'Remplir : recadrer sans étirer'])
        self.fit_combo.currentIndexChanged.connect(self._set_fit)
        controls_l.addWidget(self.fit_combo)
        self.reset_view_btn = self._button('Réinitialiser cadrage et zoom', self._reset_view)
        controls_l.addWidget(self.reset_view_btn)
        controls_l.addWidget(self._label('Sur l’aperçu : molette = zoom, clic = centrage, glisser = déplacement', 'Tiny'))
        self.flags = {}
        for attr,label in [('mirror','Effet miroir'),('grayscale','Noir & blanc'),('show_grid','Grille de composition')]:
            cb=QCheckBox(label)
            cb.toggled.connect(lambda v,k=attr:self._set(k,v))
            self.flags[attr]=cb
            controls_l.addWidget(cb)
        controls_l.addWidget(self._label('Profils', 'Section'))
        self.profiles = WheelSafeComboBox()
        controls_l.addWidget(self.profiles)
        self.profiles.currentTextChanged.connect(self.load_profile)
        row=QHBoxLayout()
        row.addWidget(self._button('Appliquer', lambda:self.load_profile(self.profiles.currentText())))
        row.addWidget(self._button('Enregistrer profil', self.save_profile, accent=True))
        controls_l.addLayout(row)
        controls_l.addWidget(self._label('Qualité de sortie / OBS / partage Discord', 'Section'))
        self.output_modes = WheelSafeComboBox()
        self.output_modes.addItems(VIDEO_MODES.keys())
        self.output_modes.currentTextChanged.connect(self._change_output_mode)
        controls_l.addWidget(self.output_modes)
        self.source_resolution = self._label('Source caméra : en attente', 'Tiny')
        controls_l.addWidget(self.source_resolution)
        controls_l.addWidget(self._label('1440p/60 : format de sortie, pas promesse de 60 images natives. Pour Nitro utiliser Go Live / partage d’écran.', 'Tiny'))
        controls_l.addWidget(self._label('Codec H.264 : évolution future', 'Tiny'))
        controls_l.addStretch()
        right_scroll.setWidget(controls)
        hbox.addWidget(right_scroll)

    def _button(self, label, func, accent=False):
        b=QPushButton(label)
        if accent: b.setObjectName('Accent')
        b.clicked.connect(func)
        return b

    def _range(self, parent, label, lo, hi, default, cb, remote=False):
        label_row=QHBoxLayout()
        label_row.addWidget(self._label(label, 'Tiny'))
        val=self._label(str(default), 'Tiny')
        val.setAlignment(Qt.AlignRight)
        label_row.addWidget(val)
        parent.addLayout(label_row)
        s=WheelSafeSlider(Qt.Horizontal)
        s.setRange(lo,hi)
        s.setValue(default)
        if remote:
            timer=QTimer(s); timer.setSingleShot(True); timer.setInterval(210)
            timer.timeout.connect(lambda:cb(s.value()))
            s.valueChanged.connect(lambda n: (val.setText(str(n)), timer.start()))
        else:
            s.valueChanged.connect(lambda n: (val.setText(str(n)), cb(n)))
        parent.addWidget(s)
        return s

    def _apply_saved(self):
        self.host.setText(self.config.get('host',''))
        self.key.setText(self.config.get('key',''))
        self.connection_method.blockSignals(True)
        self.connection_method.setCurrentIndex(1 if self.config.get('connection_mode')=='usb' else 0)
        self.connection_method.blockSignals(False)
        self._on_connection_method_changed(self.connection_method.currentIndex())
        for name,control in [
            ('zoom',self.phone_zoom),('quality',self.quality),
            ('exposure',self.phone_exposure),('fps',self.phone_fps)
        ]:
            saved=self.config.get('phone_controls',{}).get(name)
            if isinstance(saved,int):
                control.blockSignals(True)
                control.setValue(max(control.minimum(),min(control.maximum(),saved)))
                control.blockSignals(False)
        self._load_settings(self.config.get('last_settings',{}))
        self.profiles.blockSignals(True)
        self.profiles.addItems(sorted(self.config.setdefault('profiles',{}).keys()))
        self.profiles.blockSignals(False)

    def _load_settings(self, data):
        for k, v in data.items():
            if not hasattr(self.settings,k): continue
            setattr(self.settings,k,v)
        for k, slider in self.sliders.items(): slider.setValue(getattr(self.settings,k))
        for k, flag in self.flags.items(): flag.setChecked(bool(getattr(self.settings,k)))
        self.rotation.setCurrentIndex(int(self.settings.rotation)//90)
        if hasattr(self, 'fit_combo'):
            self.fit_combo.blockSignals(True)
            self.fit_combo.setCurrentIndex(1 if self.settings.fit_mode == 'cover' else 0)
            self.fit_combo.blockSignals(False)
        if hasattr(self, 'output_modes'):
            name=self.config.get('output_mode', '720p / 30 FPS')
            self.output_modes.blockSignals(True)
            self.output_modes.setCurrentText(name if name in VIDEO_MODES else '720p / 30 FPS')
            self.output_modes.blockSignals(False)
            self._change_output_mode(self.output_modes.currentText(), quiet=True)

    def _on_connection_method_changed(self,index):
        self.host.setEnabled(index == 0)
        self.usb_quality_btn.setEnabled(index == 1)
        if getattr(self,'_fully_ready',False):
            self._usb_autoconnect_enabled=(index==1)
            self._schedule_save()

    def _enable_usb_quality(self):
        if self.connection_method.currentIndex() != 1:
            return
        preset=next(name for name in VIDEO_MODES if name.startswith('1080p'))
        self.output_modes.setCurrentText(preset)
        self.quality.setValue(90)
        self.status('USB : sortie 1080p et qualité JPEG 90 (capture native selon le téléphone).')

    def _stream_base_url(self):
        return self._active_base_url or self._host_url()

    def _close_usb_tunnel(self):
        tunnel=self.usb_tunnel
        self.usb_tunnel=None
        self._active_base_url=None
        if tunnel:
            tunnel.close()

    def _set(self, attr, val):
        setattr(self.settings,attr,val)
        self._schedule_save()
        if attr in ('zoom','rotation'):
            self._render_last_frame()

    def _set_fit(self, index):
        self.settings.fit_mode = 'cover' if index == 1 else 'contain'
        self._schedule_save()
        self._render_last_frame()

    def _reset_view(self):
        self.settings.focus_x = self.settings.focus_y = .5
        self.sliders['zoom'].setValue(100)
        self._render_last_frame()

    def _point_clicked(self, u, v):
        if self.last_raw_frame is None: return
        h, w = self.last_raw_frame.shape[:2]
        x, y = source_point_from_output(u,v,w,h,self.settings,self.out_width,self.out_height)
        self.settings.focus_x, self.settings.focus_y = x, y
        self._schedule_save()
        self._render_last_frame()

    def _pan_dragged(self, dx, dy):
        if self.last_raw_frame is None: return
        h, w = self.last_raw_frame.shape[:2]
        rw, rh = rotated_dimensions(w,h,self.settings.rotation)
        _, _, cw, ch = viewport(rw,rh,self.settings,self.out_width,self.out_height)
        _, _, bw, bh = output_content_bounds(w,h,self.settings,self.out_width,self.out_height)
        self.settings.focus_x = max(0.,min(1.,self.settings.focus_x - dx*self.out_width/max(1,bw)*cw/rw))
        self.settings.focus_y = max(0.,min(1.,self.settings.focus_y - dy*self.out_height/max(1,bh)*ch/rh))
        self._schedule_save()
        self._render_last_frame()

    def _wheel_zoom(self, direction, u, v):
        if self.last_raw_frame is None: return
        h, w = self.last_raw_frame.shape[:2]
        before=source_point_from_output(u,v,w,h,self.settings,self.out_width,self.out_height)
        old=self.settings.zoom
        new=max(100,min(600,old+(20 if direction>0 else -20)))
        if new == old: return
        self.sliders['zoom'].setValue(new)
        after=source_point_from_output(u,v,w,h,self.settings,self.out_width,self.out_height)
        self.settings.focus_x=max(0.,min(1.,self.settings.focus_x+before[0]-after[0]))
        self.settings.focus_y=max(0.,min(1.,self.settings.focus_y+before[1]-after[1]))
        self._schedule_save()
        self._render_last_frame()

    def _change_output_mode(self, name, quiet=False):
        if name not in VIDEO_MODES: return
        if self.writer is not None:
            self.toggle_record()
        if self.vcam is not None:
            self._stop_virtual()
        self.out_width, self.out_height, self.out_fps = VIDEO_MODES[name]
        self._last_output_delivery = 0.0
        self._render_last_frame()
        if self.worker is not None:
            self._sync_phone_mode()
        if not quiet:
            self.status('Sortie '+name+' (la source peut être moins définie ou moins fluide)')

    def _render_last_frame(self):
        if self.last_raw_frame is not None:
            self._render_frame(self.last_raw_frame)

    def _sync_phone_mode(self):
        # Ask Android for native preview settings; status reports what is really available.
        # Keep these requests ordered to avoid racing two camera reconfigurations.
        if self.worker is None: return
        try:
            url=self._stream_base_url()+'/control?key='+quote(self.key.text().strip())
        except ValueError: return
        # JPEG preview encoding at full 1440p/60 overheats phones and blocks UIs.
        # Output resolution remains selectable, independently of phone capture.
        desired_h=min(self.out_height,1080)
        desired_fps=min(self.out_fps,30)
        def set_mode():
            try:
                for action, value in [('resolution',desired_h),('fps',desired_fps)]:
                    requests.post(url,json={'action':action,'value':str(value)},timeout=4).raise_for_status()
            except Exception as e:
                self.last_remote_error=str(e)
        threading.Thread(target=set_mode, daemon=True).start()

    def _display_battery(self, data):
        self._battery_polling = False
        if not data or self.worker is None:
            return
        pct=data.get('battery_percent',-1)
        charging=data.get('battery_charging',False)
        if isinstance(pct,int) and pct >= 0:
            self.battery_label.setText(f'🔋 {pct}%'+(' ⚡ en charge' if charging else ''))
            self.battery_label.setToolTip('Batterie du Samsung · information actualisée environ toutes les 7 secondes')
        else:
            self.battery_label.setText('🔋 --%')

    def _poll_battery(self):
        if self.worker is None or self._battery_polling:
            return
        self._battery_polling = True
        try:
            url=self._stream_base_url()+'/status?key='+quote(self.key.text().strip())
        except ValueError:
            self._battery_polling=False
            return
        def fetch():
            data=None
            try:
                r=requests.get(url,timeout=3)
                r.raise_for_status()
                data=r.json()
            except Exception:
                pass
            self.battery_received.emit(data)
        threading.Thread(target=fetch,daemon=True).start()

    def load_profile(self, name):
        values=self.config.get('profiles',{}).get(name)
        if values:
            self._load_settings(values)
            self.status('Profil chargé : '+name)

    def save_profile(self):
        name,ok=QInputDialog.getText(self,'Nouveau profil','Nom du profil :')
        if not ok or not name.strip(): return
        name=name.strip()[:50]
        self.config.setdefault('profiles',{})[name]=vars(self.settings).copy()
        if self.profiles.findText(name)<0: self.profiles.addItem(name)
        self.profiles.setCurrentText(name)
        self._save_config()
        self.status('Profil enregistré : '+name)

    def status(self, msg, color='#a8b0c6'):
        self.status_text.setText(msg)
        self.status_text.setStyleSheet('color:'+color+';')

    def _host_url(self):
        text=self.host.text().strip()
        if not text: raise ValueError('Saisis l’adresse IP du téléphone')
        if '://' in text:
            raise ValueError('Saisis uniquement l’IP ou IP:port, sans http://')
        if '/' in text or '?' in text or '@' in text or ' ' in text:
            raise ValueError('Adresse invalide')
        if ':' not in text: text+=':8765'
        return 'http://'+text

    def connect_camera(self):
        if self.worker is not None: return
        try:
            token=self.key.text().strip()
            if not token:
                raise ValueError('Saisis la clé affichée sur le téléphone')
            if self.connection_method.currentIndex()==1:
                self.usb_tunnel=open_usb_tunnel()
                addr=self.usb_tunnel.url
                self._active_base_url=addr
            else:
                addr=self._host_url()
                self._active_base_url=addr
        except (ValueError, UsbConnectionError) as e:
            self._close_usb_tunnel()
            QMessageBox.warning(self,'Connexion',str(e))
            self.status('Connexion impossible : '+str(e)[:150],'#ffa0af')
            return
        self._save_config()
        self.connection_method.setEnabled(False)
        self._camera_mode_synced = False
        self.worker=MJPEGReader(addr+'/video?key='+quote(token))
        self.worker.error.connect(self._on_error)
        self.worker.stopped.connect(self._on_stopped)
        self.worker.start()
        medium='USB' if self.usb_tunnel else 'Wi-Fi'
        self.status('Connexion '+medium+' à '+addr+'…')
        self.connection_indicator.setText('● CONNEXION '+medium.upper()+'…')

    def _on_error(self,error):
        self.status('Erreur de connexion : '+error[:180],'#ffa0af')

    def _on_stopped(self):
        if self.sender() is self.worker:
            self.connection_indicator.setText('● HORS LIGNE')
            self.worker=None
            self.connection_method.setEnabled(True)
            self._close_usb_tunnel()

    def disconnect_camera(self,manual=True):
        if manual and getattr(self,'_fully_ready',False):
            self._usb_autoconnect_enabled=False
            self._schedule_save()
        if self.worker:
            worker=self.worker
            worker.stop()
            self.worker=None
            self.retired_workers.append(worker)
            worker.finished.connect(lambda w=worker: self._retire(w))
            worker.finished.connect(worker.deleteLater)
        self._camera_mode_synced = False
        self._close_usb_tunnel()
        self.connection_method.setEnabled(True)
        self.connection_indicator.setText('● HORS LIGNE')
        self.battery_label.setText('🔋 --%')
        self.status('Caméra déconnectée')

    def _retire(self, worker):
        if worker in self.retired_workers:
            self.retired_workers.remove(worker)

    def remote(self, action, value):
        if self.worker is None:
            return
        try:
            url=self._stream_base_url()+'/control?key='+quote(self.key.text().strip())
        except ValueError: return
        def submit():
            try: requests.post(url,json={'action':action,'value':value},timeout=2).raise_for_status()
            except Exception as e: self.last_remote_error=str(e)
        threading.Thread(target=submit,daemon=True).start()

    def toggle_torch(self):
        current=self.torch_btn.text().endswith('ON')
        self.torch_btn.setText('☼ Lampe OFF' if current else '☼ Lampe ON')
        self.remote('torch','0' if current else '1')

    def _poll_latest_frame(self):
        self._drain_output()
        worker = self.worker
        if worker is None:
            return
        jpg = worker.pop_latest()
        if jpg:
            self._on_jpeg(jpg)

    def _effective_output_fps(self):
        # Report actual frame production limits rather than invented 60 FPS.
        # 1080p now uses the optimized processing pipeline; 1440p is still capped.
        cap = 12 if self.out_width >= 2560 else 30
        return min(cap, self.out_fps)

    def _on_jpeg(self, jpg):
        # Decode exactly the latest packet: no unbounded incoming frame queue.
        arr=cv2.imdecode(np.frombuffer(jpg,np.uint8),cv2.IMREAD_COLOR)
        if arr is None: return
        self.last_raw_frame=arr
        now=time.monotonic()
        self.fps_count+=1
        # Avoid repainting/processing the preview on every USB packet.
        # Always schedule frames for the virtual camera, independently of preview.
        modern = getattr(self, '_modern_ui', None)
        external_preview = modern is not None and modern.is_external_preview_visible()
        active_preview = self.image.isVisible() or external_preview
        preview_interval=1/25 if active_preview else 1/10
        redraw=(not (self.vcam or self.writer)) and now-self._last_preview_at>=preview_interval
        if redraw:
            self._last_preview_at=now
        self._render_frame(arr,draw_preview=redraw)
        if now-self._last_camera_ui_update_at>=.4:
            self._last_camera_ui_update_at=now
            self.source_resolution.setText(f'Source caméra : {arr.shape[1]} × {arr.shape[0]} (flux JPEG)')
            self.connection_indicator.setText('● CONNECTÉ')
            self.connection_indicator.setStyleSheet('color: #72e2bd;')
        if not self._camera_mode_synced:
            self._camera_mode_synced=True
            self._sync_phone_mode()

    def _render_frame(self, arr, draw_preview=True):
        if draw_preview:
            pw, ph = self._preview_width, self._preview_height
            frame = process_with_scene(arr, self.settings, pw, ph, self.scenes.snapshot())
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = QImage(rgb.data, pw, ph, rgb.strides[0], QImage.Format_RGB888).copy()
            self.last_pixmap = QPixmap.fromImage(img)
            self._update_preview()
            self.last_frame = frame

        if not (self.vcam or (self.writer and not self.record_paused)):
            return
        now = time.monotonic()
        if self._output_future is not None:
            return
        # Process every fresh source frame up to 1080p: MJPEG packets arrive in
        # bursts and a strict frame-arrival gate was dropping real captures.
        # Keep the cadence cap only for expensive 1440p upscaling.
        if self.out_width >= 2560 and now - self._last_output_delivery < 1.0 / self._effective_output_fps():
            return
        self._last_output_delivery = now
        snapshot = replace(self.settings)
        scenes_snapshot = self.scenes.snapshot()
        # At most one full-resolution composited frame in flight.
        self._output_future = self._output_pool.submit(
            process_with_scene, arr, snapshot, self.out_width, self.out_height, scenes_snapshot
        )

    def _drain_output(self):
        job = self._output_future
        if job is None or not job.done():
            return
        self._output_future = None
        try:
            output = job.result()
        except Exception as e:
            self.status('Erreur traitement vidéo : '+str(e)[:140], '#ffa0af')
            return
        if output.shape[:2] != (self.out_height, self.out_width):
            return
        # Preview shares the *already processed* output instead of running
        # all contrast, saturation and sharpening filters a second time.
        now=time.monotonic()
        modern = getattr(self, '_modern_ui', None)
        preview_visible = self.image.isVisible() or (modern is not None and modern.is_external_preview_visible())
        if now-self._last_preview_at >= (1/25 if preview_visible else 1/10):
            self._last_preview_at=now
            pw,ph=self._preview_width,self._preview_height
            preview=cv2.resize(output,(pw,ph),interpolation=cv2.INTER_AREA)
            rgb_preview=cv2.cvtColor(preview,cv2.COLOR_BGR2RGB)
            img=QImage(rgb_preview.data,pw,ph,rgb_preview.strides[0],QImage.Format_RGB888).copy()
            self.last_pixmap=QPixmap.fromImage(img)
            self._update_preview()
            self.last_frame=preview
        if self.vcam:
            try:
                rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
                self.vcam.send(np.ascontiguousarray(rgb))
                self._output_sent_count += 1
            except Exception as e:
                self._stop_virtual()
                self.status('Webcam virtuelle : '+str(e),'#ffa0af')
        if self.writer and not self.record_paused:
            try:
                self.writer.write(output)
            except Exception as e:
                self.toggle_record()
                self.status('Enregistrement : '+str(e),'#ffa0af')

    def _update_preview(self):
        if self.last_pixmap:
            self.image.setPixmap(self.last_pixmap.scaled(self.image.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'image'): self._update_preview()

    def capture(self):
        if not hasattr(self,'last_frame'):
            self.status('Pas encore d’image à capturer','#ffa0af');return
        folder=Path.home()/'Videos'/'CamStudioPro'
        folder.mkdir(parents=True,exist_ok=True)
        file=folder/('photo_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.png')
        # Photos are rendered at the selected output resolution on demand.
        photo = process_with_scene(self.last_raw_frame, self.settings, self.out_width, self.out_height, self.scenes.snapshot())
        if cv2.imwrite(str(file),photo): self.status('Photo enregistrée : '+str(file),'#79ddba')
        else: self.status('Impossible d’enregistrer cette photo','#ffa0af')

    def pause_record(self):
        # Keep one VideoWriter alive, and skip frames only while paused.
        # The MP4 timeline is derived from written frames, so pause time is excluded.
        if self.writer is None:
            return
        self.record_paused = not self.record_paused
        self.pause_btn.setText('▶  Reprendre' if self.record_paused else '⏸  Pause')
        self.status('Enregistrement en pause' if self.record_paused else
                    'Enregistrement repris dans le même fichier',
                    '#c6b1ff' if self.record_paused else '#79ddba')

    def toggle_record(self):
        if self.writer:
            self.writer.release();self.writer=None
            self.record_paused=False
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText('⏸  Pause')
            self.rec_btn.setText('●  Enregistrer')
            self.status('Vidéo enregistrée : '+str(self.record_path),'#79ddba')
            return
        if not hasattr(self,'last_frame'):
            self.status('Connecte la caméra avant l’enregistrement','#ffa0af');return
        folder=Path.home()/'Videos'/'CamStudioPro';folder.mkdir(parents=True,exist_ok=True)
        self.record_path=folder/('video_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.mp4')
        self.writer=cv2.VideoWriter(str(self.record_path),cv2.VideoWriter_fourcc(*'mp4v'),self._effective_output_fps(),(self.out_width,self.out_height))
        if not self.writer.isOpened():
            self.writer=None
            self.record_paused=False
            self.pause_btn.setEnabled(False)
            QMessageBox.warning(self,'Enregistrement','Le codec vidéo MP4 ne peut pas démarrer.');return
        self.record_paused=False
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText('⏸  Pause')
        self.rec_btn.setText('■  Arrêter vidéo')
        self.status('Enregistrement en cours : '+str(self.record_path),'#ffa2b3')

    def toggle_virtual(self):
        if self.vcam:
            self._stop_virtual();self.status('Webcam virtuelle arrêtée');return
        try:
            import pyvirtualcam
            self.vcam=pyvirtualcam.Camera(width=self.out_width,height=self.out_height,fps=self._effective_output_fps(),fmt=pyvirtualcam.PixelFormat.RGB)
            self.virtual_btn.setText('■  Arrêter webcam virtuelle')
            self.status('Webcam virtuelle active : '+self.vcam.device,'#79ddba')
        except Exception as e:
            QMessageBox.warning(self,'Webcam virtuelle', 'Impossible d’ouvrir la webcam virtuelle. Vérifie qu’OBS est installé et que sa sortie webcam n’est pas déjà utilisée.\n\n'+str(e))

    def _stop_virtual(self):
        if self.vcam:
            try: self.vcam.close()
            finally: self.vcam=None
        self.virtual_btn.setText('◉  Activer webcam virtuelle')

    def _tick(self):
        self._clock_ticks += 1
        if self._clock_ticks % 7 == 1:
            self._poll_battery()
        current=time.monotonic();dt=max(.001,current-self.fps_t)
        if self.worker:
            self._last_actual_receive_fps=self.fps_count/dt
            self._last_actual_output_fps=self._output_sent_count/dt
            self.status_text.setToolTip(
                f'Capture reçue : {self._last_actual_receive_fps:.1f} FPS réels'
                f' | webcam envoyée : {self._last_actual_output_fps:.1f} FPS'
                f' | sortie configurée : {self._effective_output_fps()} FPS max'
            )
            self.source_resolution.setToolTip(
                f'Réception réelle : {self._last_actual_receive_fps:.1f} images/s. '
                'La sortie Discord à 60 FPS ne crée pas d’images supplémentaires.'
            )
        self.fps_count=0
        self._output_sent_count=0
        self.fps_t=current

    def _show_first_tray_notice(self):
        if self.config.get('tray_notice_seen', False):
            return
        box = QMessageBox(self)
        box.setWindowTitle('CamStudio Pro · Toujours actif')
        box.setIcon(QMessageBox.Information)
        box.setText('CamStudio Pro reste actif dans la zone de notification.')
        box.setInformativeText(
            'La fenêtre disparaît, mais la caméra, la webcam virtuelle et les '
            'enregistrements peuvent continuer en arrière-plan.\n\n'
            'Pour rouvrir CamStudio, clique sur la petite flèche ^ près de '
            "l’horloge Windows, puis sur l’icône violette C.\n\n"
            'Pour tout arrêter, fais un clic droit sur cette icône et '
            'choisis « Quitter CamStudio Pro ».'
        )
        remember = QCheckBox('Ne plus afficher ce message')
        remember.setChecked(True)
        box.setCheckBox(remember)
        action = box.addButton('Compris', QMessageBox.AcceptRole)
        box.setDefaultButton(action)
        box.exec()
        if remember.isChecked():
            self.config['tray_notice_seen'] = True
            self._save_config()

    def closeEvent(self, event):
        if getattr(self,'_tray_enabled',False) and not self._really_quit:
            self._show_first_tray_notice()
            event.ignore()
            self.hide()
            if not self._tray_notified:
                self.tray.showMessage(
                    'CamStudio Pro', 'La caméra continue en arrière-plan. Clic sur l’icône pour rouvrir.',
                    QSystemTrayIcon.Information, 2000
                )
                self._tray_notified = True
            return
        if getattr(self,'_tray_enabled',False):
            self.tray.hide()
        self._save_config()
        self.frame_timer.stop()
        self._output_pool.shutdown(wait=False,cancel_futures=True)
        if hasattr(self,'usb_monitor'):
            self.usb_monitor.stop()
        if hasattr(self,'_autosave_timer'):
            self._autosave_timer.stop()
        self.disconnect_camera(manual=False)
        for worker in self.retired_workers:
            worker.wait(4500)
        if self.writer: self.writer.release();self.writer=None
        self.record_paused=False
        if self.vcam: self._stop_virtual()
        event.accept()


def main():
    app=QApplication(sys.argv)
    app.setApplicationName('CamStudio Pro')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    guard=InstanceGuard()
    try:
        first=guard.acquire()
    except RuntimeError as error:
        QMessageBox.warning(None,'CamStudio Pro',str(error))
        return 1
    if not first:
        return 0
    w=Studio()
    guard.show_requested.connect(w._show_from_tray)
    w.show()
    return app.exec()

if __name__=='__main__':
    sys.exit(main())
