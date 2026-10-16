"""CamStudio Pro V0.4 interface.

Non-destructive upgrade: rearranges an existing Studio's *widgets* into a modern
navigation shell; keeps camera capture, MJPEG networking, profiles, tray and
virtual-camera code untouched. Called immediately after Studio._build().
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QStackedWidget, QCheckBox, QComboBox,
    QSlider, QSizePolicy, QLineEdit,
)
from .features import PAGES
from .preferences import load_prefs, save_prefs
from .recordings import RecordingGallery
from .scene_editor import SceneEditor
from .i18n import LANGUAGES,apply_tree,translate

STYLES = '''
QLabel { background: transparent; }
QFrame#ModernNav { background-color: #151827; border-right: 1px solid #30344B; }
QPushButton#ModernNavButton { text-align:left; padding:12px 15px; border:0; border-radius:10px;
   background:transparent; font-weight:600; font-size:13px; color:#AAB0C9; }
QPushButton#ModernNavButton:checked { background:#393052; color:#F6F2FF; }
QPushButton#ModernNavButton:hover { background:#2F3147; }
QLabel#ModernHeading {font-size:26px; font-weight:800; color:#FFFFFF;}
QLabel#ModernMuted { color:#A3ABC4; font-size:12px; }
QLabel#ModernStat { color:#FFFFFF; font-weight:700; font-size:19px; }
QFrame#ModernCard { background:#1B2030; border:1px solid #353B55; border-radius:14px; }
QFrame#ModernBadge { background:#28223D; border:1px solid #5F4E9A; border-radius:8px; }
QPushButton#ModernAction { padding:11px 15px; background:#5E44CA; border:1px solid #8A73E8;
 border-radius:9px; color:white; font-weight:600; }
QPushButton#ModernAction:hover {background:#755BE4;}
'''


class NoWheelCombo(QComboBox):
    """The mouse wheel scrolls pages without silently changing a selected mode."""
    def wheelEvent(self, event):
        event.ignore()


def label(text: str, *, muted: bool = False, title: bool = False, wrap: bool = True) -> QLabel:
    item = QLabel(text)
    item.setObjectName('ModernHeading' if title else ('ModernMuted' if muted else ''))
    item.setWordWrap(wrap)
    return item


def button(text: str, callback, accent: bool = False) -> QPushButton:
    b = QPushButton(text)
    if accent:
        b.setObjectName('ModernAction')
    b.clicked.connect(callback)
    return b


def card(heading: str, explanation: str = ''):
    frame = QFrame()
    frame.setObjectName('ModernCard')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 17, 18, 17)
    layout.setSpacing(10)
    heading_label = QLabel(heading)
    heading_label.setStyleSheet('font-size:16px; font-weight:700; color:#F7F6FF;')
    layout.addWidget(heading_label)
    if explanation:
        layout.addWidget(label(explanation, muted=True))
    return frame, layout


def create_page(title: str, subtitle: str):
    page = QWidget()
    page.setObjectName('ModernPage')
    outer = QVBoxLayout(page)
    outer.setContentsMargins(18, 14, 18, 14)
    outer.setSpacing(0)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setStyleSheet('QScrollArea { border:0; background:transparent; }')
    body = QWidget()
    lay = QVBoxLayout(body)
    lay.setContentsMargins(9, 8, 9, 28)
    lay.setSpacing(16)
    lay.addWidget(label(title, title=True))
    lay.addWidget(label(subtitle, muted=True))
    scroll.setWidget(body)
    outer.addWidget(scroll)
    return page, lay


class V04Controller:
    def __init__(self, studio):
        self.studio = studio
        self.prefs = load_prefs()
        self.buttons = {}
        self.pages = {}
        self.previews = {}
        self.advanced_only = []
        self._mode_widgets = []
        self._last_preview_frame_key = {}
        self._recompose()
        self._timer = QTimer(studio)
        self._timer.setInterval(800)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        # Camera preview has a separate fast timer. The 800ms status timer must
        # never be responsible for updating a live video surface.
        self._preview_timer = QTimer(studio)
        self._preview_timer.setInterval(40)  # 25 Hz maximum, source-limited
        self._preview_timer.timeout.connect(self.refresh_preview)
        self._preview_timer.start()
        self.set_advanced(self.prefs['advanced_mode'], save=False)
        self.go('home')
        self.set_language(self.prefs.get('language','en'), save=False)

    def _recompose(self):
        studio = self.studio
        layout = studio.centralWidget().layout()
        if layout.count() < 3:
            raise RuntimeError('Expected sidebar, preview and controls widgets in CamStudio Studio._build()')
        widgets = []
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                widgets.append(item.widget())
        if len(widgets) != 3:
            raise RuntimeError('Unexpected CamStudio widgets: '+str(len(widgets)))
        original_nav, original_main, original_controls = widgets
        original_nav.hide()
        original_nav.setParent(None)
        original_nav.deleteLater()
        self.original_controls = original_controls
        # Individual combo-boxes hold stable index semantics. Output formats,
        # scene names and user profiles are never translated as data.
        for widget in (studio.connection_method,studio.fit_combo):
            widget.setProperty('_cs_translate_items',True)

        sidebar = QFrame()
        sidebar.setObjectName('ModernNav')
        sidebar.setFixedWidth(211)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(12, 20, 12, 19)
        nav.setSpacing(6)
        brand = label('◉  CAMSTUDIO', title=False)
        brand.setStyleSheet('font-size:19px; font-weight:800; color:#F5F4FF; padding:6px 7px;')
        nav.addWidget(brand)
        nav.addWidget(label('PRO  /  1.0 RC', muted=True))
        nav.addSpacing(20)

        self.stack = QStackedWidget()
        self.stack.setObjectName('ModernStack')
        for section in PAGES:
            action = QPushButton(section.icon+'  '+section.title)
            action.setCheckable(True)
            action.setObjectName('ModernNavButton')
            action.clicked.connect(lambda checked=False, name=section.id: self.go(name))
            nav.addWidget(action)
            self.buttons[section.id] = action
        nav.addStretch()
        nav.addWidget(label('LOCAL · PAS DE CLOUD', muted=True))
        nav.addWidget(label('Caméra active même en arrière-plan', muted=True))

        camera = QWidget()
        camera_layout = QHBoxLayout(camera)
        camera_layout.setContentsMargins(6, 6, 6, 6)
        camera_layout.setSpacing(4)
        camera_layout.addWidget(original_main, stretch=1)
        camera_layout.addWidget(original_controls)
        self.camera_page = camera

        for section in PAGES:
            if section.id == 'camera':
                page = camera
            else:
                page, body = create_page(section.title, section.subtitle)
                build = getattr(self, '_make_'+section.id)
                build(body)
                body.addStretch(1)
            self.pages[section.id] = page
            self.stack.addWidget(page)

        for widget in (
            self.gallery.filter, self.scene_editor.background,
            self.connection_selector
        ):
            widget.setProperty('_cs_translate_items',True)
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, stretch=1)
        studio.setStyleSheet(studio.styleSheet() + STYLES)
        studio.setWindowTitle('CamStudio Pro · Camera studio (V1.0)')
        studio.resize(1460, 870)
        studio.setMinimumSize(960, 640)

    def go(self, name: str):
        if name not in self.pages:
            return
        self.stack.setCurrentWidget(self.pages[name])
        for key, action in self.buttons.items():
            action.setChecked(key == name)
        self._last_preview_frame_key.clear()
        self.refresh()
        if name == 'record' and hasattr(self,'gallery'):
            self.gallery.reload(force=True)
        self.refresh_preview()

    def _add_preview(self, lay):
        preview = QLabel('Connecte une caméra pour afficher le retour vidéo.')
        preview.setMinimumHeight(180)
        preview.setMaximumHeight(365)
        preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        preview.setAlignment(Qt.AlignCenter)
        preview.setStyleSheet('background:#090C13; border:1px solid #353B54; border-radius:12px; color:#858EA8;')
        lay.addWidget(preview)
        self.previews[lay] = preview
        return preview

    def _make_home(self, lay):
        hero, inside = card('Vue d’ensemble', 'Connexion, batterie, caméra et actions rapides')
        self.home_preview = self._add_preview(inside)
        stats = QHBoxLayout()
        self.home_conn = label('● Hors ligne')
        self.home_batt = label('Batterie : -- %')
        self.home_source = label('Source : en attente')
        for item in (self.home_conn,self.home_batt,self.home_source):
            stats.addWidget(item)
        inside.addLayout(stats)
        self.home_fps=label('Flux réel : -- FPS · Webcam virtuelle : -- FPS',muted=True)
        inside.addWidget(self.home_fps)
        self.home_diagnostics = label('Diagnostic : aucune source', muted=True)
        inside.addWidget(self.home_diagnostics)
        row = QHBoxLayout()
        row.addWidget(button('Connecter la caméra', self.studio.connect_camera, True))
        row.addWidget(button('Déconnecter', self.studio.disconnect_camera))
        row.addWidget(button('Capture photo', self.studio.capture))
        inside.addLayout(row)
        lay.addWidget(hero)
        second, s = card('Webcam virtuelle', 'Sortie pour Discord, OBS et les applications compatibles.')
        s.addWidget(button('Activer / arrêter la webcam virtuelle', self.studio.toggle_virtual))
        lay.addWidget(second)
        guide, guide_lay = card('Fluidité Discord', 'Tant que le téléphone produit environ 20 à 30 FPS réels, choisis 30 FPS dans Discord, et non 60 FPS. Évite les filtres trop lourds ou un éclairage faible.')
        lay.addWidget(guide)

    def _make_studio(self, lay):
        box, b = card('Traitement d’image', 'Les profils existants fonctionnent immédiatement.')
        row=QHBoxLayout()
        from processor import PRESETS
        for name in ('Naturel','Studio','Cinéma','Streaming'):
            if name in PRESETS:
                row.addWidget(button(name, lambda _=False, n=name: self.studio._load_settings(vars(PRESETS[n]).copy())))
        b.addLayout(row)
        self.studio_preview = self._add_preview(b)
        b.addWidget(button('Ouvrir les réglages manuels de la caméra',lambda:self.go('camera'),True))
        lay.addWidget(box)
        self._add_advanced(lay, 'Ajustements fins', 'Les paramètres ISO, obturation et contrôle Camera2 nécessitent une implémentation Android distincte.')

    def _make_scenes(self, lay):
        box,b = card('Profils disponibles', 'Appliquer les profils sauvegardés sans interrompre la vidéo.')
        self.profile_select = NoWheelCombo()
        self.profile_select.addItems(sorted(self.studio.config.get('profiles', {}).keys()))
        b.addWidget(self.profile_select)
        row = QHBoxLayout()
        row.addWidget(button('Appliquer',lambda:self.studio.load_profile(self.profile_select.currentText()),True))
        row.addWidget(button('Nouveau profil',self._save_profile))
        b.addLayout(row)
        lay.addWidget(box)
        editor_card, editor_layout = card(
            'Éditeur de scènes',
            'Crée des scènes avec une caméra, des images et des textes. '
            'Déplace les éléments à la souris ; tes scènes sont sauvegardées automatiquement.'
        )
        self.scene_editor = SceneEditor(self.studio)
        editor_layout.addWidget(self.scene_editor)
        lay.addWidget(editor_card)

    def _save_profile(self):
        self.studio.save_profile()
        self.profile_select.clear()
        self.profile_select.addItems(sorted(self.studio.config.get('profiles', {}).keys()))

    def _make_outputs(self, lay):
        box,b=card('Webcam virtuelle','Contrôle de la webcam système utilisée par Discord et OBS.')
        self.output_state=label('Sortie inactive',muted=True)
        b.addWidget(self.output_state)
        b.addWidget(button('Activer / arrêter la webcam virtuelle', self.studio.toggle_virtual, True))
        b.addWidget(label('Résolution de sortie',muted=True))
        self.output_select=NoWheelCombo()
        self.output_select.addItems([self.studio.output_modes.itemText(i) for i in range(self.studio.output_modes.count())])
        self.output_select.setCurrentText(self.studio.output_modes.currentText())
        self.output_select.currentTextChanged.connect(self.studio.output_modes.setCurrentText)
        self.studio.output_modes.currentTextChanged.connect(self._sync_output)
        b.addWidget(self.output_select)
        lay.addWidget(box)
        self._add_advanced(lay,'Diagnostic sortie','1440p / 60 FPS dans la liste correspond à un format proposé, pas à une capture native garantie.')

    def _sync_output(self, new):
        self.output_select.blockSignals(True)
        self.output_select.setCurrentText(new)
        self.output_select.blockSignals(False)

    def _make_record(self, lay):
        box,b=card('Photos et vidéos','Captures via les fonctions existantes de CamStudio.')
        row=QHBoxLayout()
        row.addWidget(button('Prendre une photo',self.studio.capture,True))
        row.addWidget(button('Démarrer / arrêter la vidéo',self.studio.toggle_record))
        self.record_pause_btn=button('⏸  Pause',self.studio.pause_record)
        self.record_pause_btn.setEnabled(False)
        row.addWidget(self.record_pause_btn)
        b.addLayout(row)
        self.record_status=label('Enregistrement : inactif',muted=True)
        b.addWidget(self.record_status)
        lay.addWidget(box)
        library, body = card('Mes enregistrements', 'Toutes tes captures locales avec miniatures, dates, lecture et accès aux fichiers.')
        self.gallery = RecordingGallery(self.studio)
        body.addWidget(self.gallery)
        lay.addWidget(library)
        self._add_advanced(lay,'Enregistrement pro','H.264/H.265 matériel, choix du débit et des codecs : futures évolutions.')

    def _make_connections(self, lay):
        box,b=card('Connexion du téléphone','Les identifiants restent stockés uniquement dans ton profil utilisateur local.')
        self.conn_info=label('Statut : hors ligne',muted=True)
        b.addWidget(self.conn_info)
        b.addWidget(label('Adresse Wi-Fi du téléphone (ignorée si USB est choisi)',muted=True))
        self.host_edit=QLineEdit(self.studio.host.text())
        self.host_edit.setPlaceholderText('192.168.1.50')
        self.host_edit.textChanged.connect(self.studio.host.setText)
        self.studio.host.textChanged.connect(self.host_edit.setText)
        b.addWidget(self.host_edit)
        b.addWidget(label('Clé privée affichée par l’application Android',muted=True))
        self.key_edit=QLineEdit(self.studio.key.text())
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.textChanged.connect(self.studio.key.setText)
        self.studio.key.textChanged.connect(self.key_edit.setText)
        b.addWidget(self.key_edit)
        key_buttons=QHBoxLayout()
        self.key_show_btn=button('Afficher la clé',self.studio._toggle_key_visibility)
        key_buttons.addWidget(self.key_show_btn)
        key_buttons.addWidget(button('Copier la clé',self._copy_pairing_key))
        key_buttons.addStretch(1)
        b.addLayout(key_buttons)
        b.addWidget(label('Ne communique jamais cette clé publiquement.',muted=True))
        b.addWidget(label('USB : connexion automatique dès que le téléphone autorise ADB et que la clé est enregistrée.',muted=True))
        if hasattr(self.studio,'connection_method'):
            b.addWidget(label('Transport',muted=True))
            selector=NoWheelCombo()
            selector.addItems([self.studio.connection_method.itemText(i) for i in range(self.studio.connection_method.count())])
            selector.setCurrentIndex(self.studio.connection_method.currentIndex())
            selector.currentIndexChanged.connect(self.studio.connection_method.setCurrentIndex)
            b.addWidget(selector)
            self.connection_selector=selector
        else:
            b.addWidget(label('Le sélecteur USB sera disponible après installation de la V0.3.1 sur ce projet.',muted=True))
        row=QHBoxLayout()
        row.addWidget(button('Connecter',self.studio.connect_camera,True))
        row.addWidget(button('Déconnecter',self.studio.disconnect_camera))
        b.addLayout(row)
        lay.addWidget(box)
        self._add_advanced(lay,'Diagnostic réseau','Le transport USB passe par ADB local. Ne jamais ouvrir le serveur MJPEG directement sur Internet.')

    def _language_selected(self,index):
        code=self.language_combo.itemData(index)
        if code:
            self.set_language(code)

    def set_language(self,code,*,save=True):
        if code not in {key for key,_ in LANGUAGES}:
            code='en'
        self.prefs['language']=code
        if hasattr(self,'language_combo'):
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(self.language_combo.findData(code))
            self.language_combo.blockSignals(False)
        apply_tree(self.studio,code)
        # Re-applying after a view update also localizes rapidly changing status.
        if save:
            save_prefs(self.prefs)

    def _copy_pairing_key(self):
        token=self.studio.key.text()
        if not token:
            return
        QApplication.clipboard().setText(token)
        # Clipboard may leak secrets into other applications. Clear only if unchanged.
        QTimer.singleShot(30000,lambda: QApplication.clipboard().clear()
                          if QApplication.clipboard().text()==token else None)

    def _make_settings(self, lay):
        language_card,language_body=card(
            'Language',
            'Choose your preferred language. English is used by default. Changes apply immediately.'
        )
        language_body.addWidget(label('Language'))
        self.language_combo=NoWheelCombo()
        for code,native_name in LANGUAGES:
            self.language_combo.addItem(native_name,code)
        self.language_combo.setCurrentIndex(
            max(0,self.language_combo.findData(self.prefs.get('language','en')))
        )
        self.language_combo.currentIndexChanged.connect(self._language_selected)
        language_body.addWidget(self.language_combo)
        language_body.addWidget(label('Translations are built in and work offline.'))
        lay.addWidget(language_card)
        box,b=card('Mode d’utilisation','Une interface simple pour démarrer ; des options supplémentaires pour les utilisateurs expérimentés.')
        self.mode_label=label('Mode actuel : Simple')
        b.addWidget(self.mode_label)
        self.advanced_checkbox=QCheckBox('Activer le mode avancé')
        self.advanced_checkbox.setChecked(self.prefs['advanced_mode'])
        self.advanced_checkbox.toggled.connect(self.set_advanced)
        b.addWidget(self.advanced_checkbox)
        b.addWidget(label('Simple : aperçu et actions essentielles. Avancé : contrôles complets et diagnostics disponibles.',muted=True))
        lay.addWidget(box)
        visual,v=card('Apparence','La V0.4 Preview utilise un thème sombre violet unique, optimisé pour le streaming.')
        self.diag_checkbox=QCheckBox('Afficher les informations techniques dans l’accueil')
        self.diag_checkbox.setChecked(self.prefs['show_diagnostics'])
        self.diag_checkbox.toggled.connect(self._set_diag)
        v.addWidget(self.diag_checkbox)
        self.advanced_only.append(visual)
        lay.addWidget(visual)
        about,a=card('Projet et confidentialité','Préparation à une publication open source.')
        a.addWidget(label('Aucun mot de passe, clé USB/ADB, IP personnelle ou identifiant du téléphone ne doit entrer dans GitHub.',muted=True))
        a.addWidget(label('Version de travail : V1.0 GitHub — moteur de caméra V0.3.1 conservé.',muted=True))
        lay.addWidget(about)
        self.mode_label.setText('Mode actuel : '+('Avancé' if self.prefs['advanced_mode'] else 'Simple'))

    def _add_planned(self,lay,title,text):
        frame,b=card(title+'  ·  À venir',text)
        lay.addWidget(frame)

    def _add_advanced(self,lay,title,text):
        frame,b=card(title+'  ·  Mode avancé',text)
        self.advanced_only.append(frame)
        lay.addWidget(frame)

    def _set_diag(self,enabled):
        self.prefs['show_diagnostics']=bool(enabled)
        save_prefs(self.prefs)
        self.refresh()

    def set_advanced(self, enabled: bool, *, save: bool = True):
        enabled=bool(enabled)
        self.prefs['advanced_mode']=enabled
        for widget in self.advanced_only:
            widget.setVisible(enabled)
        self.original_controls.setVisible(enabled)
        if hasattr(self,'mode_label'):
            self.mode_label.setText('Mode actuel : '+('Avancé' if enabled else 'Simple'))
        if hasattr(self,'advanced_checkbox'):
            self.advanced_checkbox.blockSignals(True)
            self.advanced_checkbox.setChecked(enabled)
            self.advanced_checkbox.blockSignals(False)
        if save:
            save_prefs(self.prefs)
        self.refresh()

    def refresh(self):
        studio=self.studio
        if hasattr(self,'home_conn'):
            connected=studio.worker is not None
            self.home_conn.setText('● Caméra '+('connectée' if connected else 'hors ligne'))
            self.home_batt.setText(studio.battery_label.text())
            width=getattr(studio,'out_width',0)
            height=getattr(studio,'out_height',0)
            self.home_source.setText(f'Sortie : {width} × {height}' if width else 'Source : en attente')
        if hasattr(self,'home_fps'):
            self.home_fps.setText(
                f'Images reçues : {getattr(studio,"_last_actual_receive_fps",0):.1f} FPS · '
                f'Webcam envoyée : {getattr(studio,"_last_actual_output_fps",0):.1f} FPS '
                '(Discord : 30 FPS conseillé)'
                if studio.worker is not None else 'Flux réel : en attente de connexion'
            )
        if hasattr(self,'output_state'):
            self.output_state.setText('Webcam virtuelle : '+('active' if studio.vcam is not None else 'inactive'))
        if hasattr(self,'record_status'):
            active=studio.writer is not None
            paused=active and studio.record_paused
            self.record_status.setText('Enregistrement : '+('en pause' if paused else ('en cours' if active else 'inactif')))
            self.record_pause_btn.setEnabled(active)
            self.record_pause_btn.setText('▶  Reprendre' if paused else '⏸  Pause')
            if self.stack.currentWidget() is self.pages['record']:
                self.gallery.reload()
        if hasattr(self,'home_diagnostics'):
            self.home_diagnostics.setVisible(self.prefs.get('advanced_mode',False) and self.prefs.get('show_diagnostics',False))
            raw=getattr(studio,'last_raw_frame',None)
            if raw is not None:
                self.home_diagnostics.setText(f'Capture : {raw.shape[1]} × {raw.shape[0]} · sortie vidéo : {studio.out_width} × {studio.out_height}')
        if hasattr(self,'conn_info'):
            self.conn_info.setText('Statut : '+('connecté' if studio.worker is not None else 'hors ligne'))
        # Status changes made by the camera reader also receive translation.
        apply_tree(studio,self.prefs.get('language','en'))

    def is_external_preview_visible(self):
        """True only for a displayed video surface (Accueil or Studio)."""
        if not self.studio.isVisible():
            return False
        current = self.stack.currentWidget()
        return current is self.pages['home'] or current is self.pages['studio']

    def refresh_preview(self):
        """Display latest real video frame at up to 25 Hz without redoing image filters."""
        if not self.is_external_preview_visible():
            return
        pix = getattr(self.studio, 'last_pixmap', None)
        if pix is None or pix.isNull():
            return
        # Only the preview of the current page is updated; no hidden-widget work.
        current = self.stack.currentWidget()
        preview = self.home_preview if current is self.pages['home'] else self.studio_preview
        if not preview.isVisible():
            return
        # Render at the actual label dimensions, and avoid stretching the source.
        width = max(1, preview.width()-4)
        height = max(1, preview.height()-4)
        key = (pix.cacheKey(), width, height)
        if self._last_preview_frame_key.get(preview) == key:
            return
        self._last_preview_frame_key[preview] = key
        preview.setPixmap(pix.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation))


def mount_v04(studio):
    """Hook inserted after Studio._build(), before Studio._apply_saved()."""
    if hasattr(studio,'_modern_ui'):
        return studio._modern_ui
    controller=V04Controller(studio)
    studio._modern_ui=controller
    return controller
