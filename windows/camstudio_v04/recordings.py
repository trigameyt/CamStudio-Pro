"""Local recording gallery for CamStudio Pro.

Recordings never leave the PC. Only local files from ~/Videos/CamStudioPro
are indexed, and thumbnails are kept in memory, not written to disk.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time

import cv2
from PySide6.QtCore import Qt, QSize, QTimer, QUrl, QPointF
from PySide6.QtGui import QPixmap, QImage, QImageReader, QPainter, QColor, QDesktopServices, QIcon, QPen, QPolygonF
from PySide6.QtWidgets import (
    QWidget, QDialog, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSlider, QMessageBox, QSizePolicy,
)
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from .controls import VideoSeekSlider

VIDEO_SUFFIXES = frozenset({'.mp4', '.mov', '.mkv', '.avi'})
PHOTO_SUFFIXES = frozenset({'.png', '.jpg', '.jpeg', '.webp'})
ALL_SUFFIXES = VIDEO_SUFFIXES | PHOTO_SUFFIXES


def recordings_folder() -> Path:
    return Path.home() / 'Videos' / 'CamStudioPro'


@dataclass(frozen=True)
class Recording:
    path: Path
    kind: str
    size: int
    modified: float

    @property
    def date_text(self) -> str:
        return datetime.fromtimestamp(self.modified).strftime('%d/%m/%Y  %H:%M')

    @property
    def size_text(self) -> str:
        if self.size >= 1024 * 1024:
            return f'{self.size / 1048576:.1f} Mo'
        return f'{max(1, round(self.size / 1024))} Ko'


def scan_recordings(folder: Path | None = None, *, excluded: Path | None = None) -> list[Recording]:
    folder = Path(folder or recordings_folder())
    if not folder.is_dir():
        return []
    excluded = Path(excluded).resolve() if excluded else None
    found = []
    try:
        paths = tuple(folder.iterdir())
    except OSError:
        return []
    for path in paths:
        try:
            if path.is_symlink() or path.suffix.lower() not in ALL_SUFFIXES or not path.is_file():
                continue
            if excluded is not None and path.resolve() == excluded:
                continue
            st = path.stat()
            if st.st_size == 0:
                continue
        except OSError:
            continue
        found.append(Recording(path, 'video' if path.suffix.lower() in VIDEO_SUFFIXES else 'photo',
                               st.st_size, st.st_mtime))
    return sorted(found, key=lambda item: (item.modified, item.path.name), reverse=True)


def _thumbnail(item: Recording, width: int = 216, height: int = 122) -> QPixmap:
    """Create one in-memory thumbnail, keeping aspect ratio."""
    source = QImage()
    if item.kind == 'photo':
        reader = QImageReader(str(item.path))
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid() and (size.width() > width * 2 or size.height() > height * 2):
            scaled = size.scaled(QSize(width * 2, height * 2), Qt.KeepAspectRatio)
            reader.setScaledSize(scaled)
        source = reader.read()
    else:
        cap = cv2.VideoCapture(str(item.path))
        try:
            if cap.isOpened():
                ok, frame = cap.read()
                if ok and frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w = frame.shape[:2]
                    source = QImage(frame.data, w, h, frame.strides[0], QImage.Format_RGB888).copy()
        finally:
            cap.release()
    canvas = QPixmap(width, height)
    canvas.fill(QColor('#090D16'))
    if not source.isNull():
        source = source.scaled(QSize(width, height), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter = QPainter(canvas)
        painter.drawImage((width-source.width())//2, (height-source.height())//2, source)
        if item.kind == 'video':
            painter.setRenderHint(QPainter.Antialiasing,True)
            cx, cy = width / 2, height / 2
            painter.setPen(QPen(QColor(235,228,255,220),1.5))
            painter.setBrush(QColor(20,17,39,185))
            painter.drawEllipse(QPointF(cx,cy),24,24)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#FFFFFF'))
            painter.drawPolygon(QPolygonF([
                QPointF(cx-5, cy-9), QPointF(cx-5,cy+9), QPointF(cx+10,cy)
            ]))
        painter.end()
    return canvas


def _external_open(path: Path) -> bool:
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def _fit_image(path: Path, max_width: int = 1080, max_height: int = 720) -> QPixmap:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid():
        reader.setScaledSize(size.scaled(QSize(max_width, max_height), Qt.KeepAspectRatio))
    img = reader.read()
    return QPixmap.fromImage(img)


class PhotoViewer(QDialog):
    def __init__(self, item: Recording, parent=None):
        super().__init__(parent)
        self.setWindowTitle('CamStudio Pro · Photo · ' + item.path.name)
        self.resize(920, 670)
        outer = QVBoxLayout(self)
        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumSize(360, 280)
        preview.setStyleSheet('background:#090D16;border-radius:12px;')
        pix = _fit_image(item.path, 820, 540)
        if not pix.isNull():
            preview.setPixmap(pix)
        else:
            preview.setText('Impossible de lire cette photo.')
        outer.addWidget(preview, 1)
        actions = QHBoxLayout()
        open_button = QPushButton('Ouvrir avec Windows')
        open_button.clicked.connect(lambda: _external_open(item.path))
        actions.addWidget(open_button)
        actions.addStretch()
        close_btn = QPushButton('Fermer')
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)
        outer.addLayout(actions)


def _timestamp(milliseconds: int) -> str:
    seconds = max(0, int(milliseconds) // 1000)
    return f'{seconds // 60:02d}:{seconds % 60:02d}'


class VideoViewer(QDialog):
    """Silent Qt video player; Windows player fallback for unsupported codecs."""
    def __init__(self, item: Recording, parent=None):
        super().__init__(parent)
        self.setWindowTitle('CamStudio Pro · Lecture · ' + item.path.name)
        self.resize(960, 700)
        self.player = QMediaPlayer(self)
        layout = QVBoxLayout(self)
        self.screen = QVideoWidget()
        self.screen.setMinimumSize(460, 260)
        self.player.setVideoOutput(self.screen)
        layout.addWidget(self.screen, 1)
        self.message = QLabel('Lecture de ' + item.path.name)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.seek = VideoSeekSlider(Qt.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderMoved.connect(self.player.setPosition)
        layout.addWidget(self.seek)
        bar = QHBoxLayout()
        self.play_button = QPushButton('⏸ Pause')
        self.play_button.clicked.connect(self._toggle)
        bar.addWidget(self.play_button)
        self.position_label = QLabel('00:00 / 00:00')
        bar.addWidget(self.position_label)
        bar.addStretch()
        external = QPushButton('Ouvrir avec Windows')
        external.clicked.connect(lambda: _external_open(item.path))
        bar.addWidget(external)
        close_btn = QPushButton('Fermer')
        close_btn.clicked.connect(self.accept)
        bar.addWidget(close_btn)
        layout.addLayout(bar)
        self.player.durationChanged.connect(self._duration_changed)
        self.player.positionChanged.connect(self._position_changed)
        self.player.playbackStateChanged.connect(self._state_changed)
        self.player.errorOccurred.connect(self._error)
        self.player.setSource(QUrl.fromLocalFile(str(item.path)))
        self.player.play()

    def _toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _state_changed(self, state):
        self.play_button.setText('⏸ Pause' if state == QMediaPlayer.PlayingState else '▶ Lire')

    def _duration_changed(self, duration):
        self.seek.setMaximum(max(0,duration))
        self.position_label.setText(_timestamp(self.player.position())+' / '+_timestamp(duration))

    def _position_changed(self, position):
        if not self.seek.isSliderDown():
            self.seek.setValue(position)
        self.position_label.setText(_timestamp(position)+' / '+_timestamp(self.player.duration()))

    def _error(self, error, message):
        if error != QMediaPlayer.NoError:
            self.message.setText('Ce fichier ne peut pas être lu ici. Utilise « Ouvrir avec Windows ». ' + message[:180])

    def done(self, result):
        self.player.stop()
        self.player.setVideoOutput(None)
        super().done(result)


class SafeFilterCombo(QComboBox):
    """A consistent native combobox with a custom centered chevron."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('GalleryFilter')
        self.setFixedWidth(126)
        self.setMinimumHeight(38)
        self.setStyleSheet('''
            QComboBox#GalleryFilter { background:#292E43; border:1px solid #464C66;
                border-radius:9px; padding:4px 32px 4px 12px; color:#F6F3FF; }
            QComboBox#GalleryFilter:hover { border-color:#9273EE; }
            QComboBox#GalleryFilter::drop-down { width:29px; border:0;
                subcontrol-origin:padding; subcontrol-position:top right; background:transparent; }
            QComboBox#GalleryFilter::down-arrow { image:none; width:0; height:0; }
            QComboBox#GalleryFilter QAbstractItemView { background:#22263A;
                border:1px solid #65589B; color:#F6F3FF; padding:5px;
                selection-background-color:#6249BB; outline:0; }
        ''')
    def wheelEvent(self,event):
        event.ignore()
    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing,True)
        painter.setPen(QPen(QColor('#CBB8FF'),2))
        x,y=self.width()-18,self.height()/2
        painter.drawLine(int(x-5),int(y-2),int(x),int(y+3))
        painter.drawLine(int(x),int(y+3),int(x+5),int(y-2))
        painter.end()


class RecordingGallery(QWidget):
    PAGE_SIZE = 42

    def __init__(self, studio=None, *, folder: Path | None = None, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.folder = Path(folder) if folder is not None else recordings_folder()
        self._all = []
        self._signature = None
        self._last_scan_at = 0.0
        self._loaded = 0
        self._generation = 0
        self._used_columns = 2
        self._pending_thumbnails = []
        self._thumb_timer = QTimer(self)
        self._thumb_timer.setInterval(8)
        self._thumb_timer.timeout.connect(self._load_next_thumbnail)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(12)
        top = QHBoxLayout()
        self.count = QLabel('Bibliothèque des enregistrements')
        self.count.setStyleSheet('font-weight:700;font-size:15px;')
        top.addWidget(self.count)
        top.addStretch()
        self.filter = SafeFilterCombo()
        self.filter.addItems(['Tous', 'Vidéos', 'Photos'])
        self.filter.currentIndexChanged.connect(self._draw)
        top.addWidget(self.filter)
        refresh = QPushButton('↻ Actualiser')
        refresh.clicked.connect(lambda: self.reload(force=True))
        top.addWidget(refresh)
        open_folder = QPushButton('Ouvrir le dossier')
        open_folder.clicked.connect(self.open_folder)
        top.addWidget(open_folder)
        outer.addLayout(top)

        self.description = QLabel('Photos et vidéos conservées sur cet ordinateur.')
        self.description.setWordWrap(True)
        self.description.setStyleSheet('color:#B1B7CF;')
        outer.addWidget(self.description)
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(14)
        outer.addLayout(self.grid)
        self.more = QPushButton('Afficher plus d’enregistrements')
        self.more.clicked.connect(self._show_more)
        self.more.hide()
        outer.addWidget(self.more)
        self.empty = QLabel('Aucun enregistrement pour le moment.\nUtilise « Prendre une photo » ou « Démarrer la vidéo ».')
        self.empty.setWordWrap(True)
        self.empty.setStyleSheet('color:#ADB3CD; padding:26px 10px;')
        outer.addWidget(self.empty)
        self.reload(force=True)

    def open_folder(self):
        self.folder.mkdir(parents=True,exist_ok=True)
        return _external_open(self.folder)

    def _exclusion(self):
        if self.studio and getattr(self.studio, 'writer', None) is not None:
            return getattr(self.studio, 'record_path', None)
        return None

    def reload(self, *, force=False):
        if not force and time.monotonic() - self._last_scan_at < 2.5:
            return
        self._last_scan_at = time.monotonic()
        files = scan_recordings(self.folder,excluded=self._exclusion())
        signature = tuple((str(f.path),f.size,f.modified) for f in files)
        if force or signature != self._signature:
            self._all = files
            self._signature = signature
            self._loaded = self.PAGE_SIZE
            self._draw()

    def _filtered(self):
        filt=self.filter.currentIndex()
        return [i for i in self._all if filt==0 or (filt==1 and i.kind=='video') or (filt==2 and i.kind=='photo')]

    def _clear_grid(self):
        while self.grid.count():
            item=self.grid.takeAt(0)
            if item.widget():
                # Hide immediately; deferred deletion otherwise paints stale tiles
                # briefly over the new layout on resize or filter changes.
                widget=item.widget()
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _draw(self):
        self._thumb_timer.stop()
        self._generation += 1
        self._pending_thumbnails.clear()
        self._clear_grid()
        filtered=self._filtered()
        count=len(filtered)
        video_count=sum(item.kind=='video' for item in self._all)
        photo_count=len(self._all)-video_count
        self.count.setText(f'Bibliothèque · {video_count} vidéo(s), {photo_count} photo(s)')
        self.empty.setVisible(count==0)
        self.more.setVisible(count>self._loaded)
        for index,item in enumerate(filtered[:self._loaded]):
            tile=QFrame()
            tile.setObjectName('RecordingTile')
            tile.setStyleSheet('QFrame#RecordingTile {background:#1E2334;border:1px solid #363D58;border-radius:12px;}')
            col=QVBoxLayout(tile)
            col.setContentsMargins(10,10,10,10)
            col.setSpacing(6)
            # The entire thumbnail is one accessible clickable target.
            thumb=QPushButton('Chargement…')
            thumb.setAccessibleName(('Lire la vidéo ' if item.kind=='video' else 'Voir la photo ')+item.path.name)
            thumb.setToolTip('Cliquer pour '+('lire cette vidéo' if item.kind=='video' else 'voir cette photo'))
            thumb.setCursor(Qt.PointingHandCursor)
            thumb.setFixedSize(216,122)
            thumb.setStyleSheet('''
                QPushButton { background:#090D16; border:1px solid #30374F;
                    border-radius:9px; padding:0; color:#A5AAC5; }
                QPushButton:hover { background:#26223F; border:2px solid #9B7BFF; }
                QPushButton:pressed { border:2px solid #D6C6FF; }
            ''')
            thumb.clicked.connect(lambda _=False,f=item:self.open_item(f))
            col.addWidget(thumb)
            name=QLabel(item.path.name)
            name.setToolTip(str(item.path))
            name.setWordWrap(True)
            name.setMaximumHeight(42)
            name.setStyleSheet('font-weight:600;font-size:12px;')
            col.addWidget(name)
            metadata=QLabel(f'{item.date_text}  ·  {item.size_text}')
            metadata.setStyleSheet('color:#AEB5C9;font-size:11px;')
            col.addWidget(metadata)
            actions=QHBoxLayout()
            view=QPushButton('▶ Regarder' if item.kind=='video' else '◉ Voir')
            view.clicked.connect(lambda _=False,f=item:self.open_item(f))
            actions.addWidget(view)
            reveal=QPushButton('Dossier')
            reveal.setToolTip('Afficher ce fichier dans l’Explorateur Windows')
            reveal.clicked.connect(lambda _=False,f=item:self.reveal_item(f))
            actions.addWidget(reveal)
            col.addLayout(actions)
            col.addStretch()
            columns = 3 if self.width() >= 790 else 2
            self._used_columns = columns
            self.grid.addWidget(tile,index//columns,index%columns)
            self._pending_thumbnails.append((self._generation,thumb,item))
        if self._pending_thumbnails:
            self._thumb_timer.start()

    def _load_next_thumbnail(self):
        if not self._pending_thumbnails:
            self._thumb_timer.stop()
            return
        generation,label,item=self._pending_thumbnails.pop(0)
        if generation==self._generation:
            try:
                label.setText('')
                label.setIcon(QIcon(_thumbnail(item)))
                label.setIconSize(QSize(214,120))
            except (OSError,RuntimeError,cv2.error):
                label.setText('Aperçu indisponible')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        columns = 3 if self.width() >= 790 else 2
        if self._used_columns != columns:
            QTimer.singleShot(0, self._draw)

    def _show_more(self):
        self._loaded+=self.PAGE_SIZE
        self._draw()

    def open_item(self, item: Recording):
        if not item.path.is_file():
            QMessageBox.warning(self,'Fichier introuvable','Ce fichier n’existe plus. Actualise la bibliothèque.')
            self.reload(force=True)
            return
        dialog = VideoViewer(item,self) if item.kind=='video' else PhotoViewer(item,self)
        dialog.exec()

    def reveal_item(self, item: Recording):
        import subprocess
        if item.path.is_file():
            # Windows Explorer selects the recording without launching the video decoder.
            if __import__('os').name=='nt':
                subprocess.Popen(['explorer.exe', '/select,', str(item.path)])
            else:
                _external_open(self.folder)
        else:
            self.reload(force=True)
