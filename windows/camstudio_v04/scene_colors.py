"""Compact color controls for the CamStudio Pro scene editor.

A swatch, validated hex entry, presets and the native color dialog are all
bound to a single signal. This never modifies image files or Windows settings.
"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QColorDialog,
)

PRESET_COLORS = (
    '#FFFFFF', '#101321', '#15112D', '#845CF7',
    '#FF4B75', '#24B6E8', '#36DAA8', '#FFCB65',
)
HEX_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')


def validate_color(value: str) -> str | None:
    """Accept opaque RGB hex only; never pass incomplete values to Qt painter."""
    value = value.strip()
    if not HEX_PATTERN.fullmatch(value):
        return None
    return value.upper()


class SceneColorPicker(QWidget):
    color_changed = Signal(str)

    def __init__(self, title: str, default='#FFFFFF', parent=None):
        super().__init__(parent)
        self.title=title
        self._current=validate_color(default) or '#FFFFFF'
        self._changing=False
        outer=QVBoxLayout(self)
        outer.setContentsMargins(0,4,0,4)
        outer.setSpacing(5)

        name=QLabel(title)
        name.setStyleSheet('color:#DBDDF0;font-weight:600;')
        outer.addWidget(name)

        row=QHBoxLayout()
        row.setSpacing(7)
        self.swatch=QPushButton()
        self.swatch.setFixedSize(48,36)
        self.swatch.setToolTip('Choisir une couleur personnalisée')
        self.swatch.setAccessibleName('Sélecteur de couleur : '+title)
        self.swatch.clicked.connect(self.open_dialog)
        row.addWidget(self.swatch)

        self.hex=QLineEdit()
        self.hex.setMaxLength(7)
        self.hex.setFixedWidth(112)
        self.hex.setPlaceholderText('#RRGGBB')
        self.hex.setToolTip('Code couleur hexadécimal (exemple : #845CF7)')
        self.hex.editingFinished.connect(self.apply_hex)
        row.addWidget(self.hex)

        self.custom=QPushButton('Personnaliser…')
        self.custom.clicked.connect(self.open_dialog)
        row.addWidget(self.custom)
        row.addStretch(1)
        outer.addLayout(row)

        self.presets=QHBoxLayout()
        self.presets.setSpacing(5)
        self.preset_buttons=[]
        for color in PRESET_COLORS:
            b=QPushButton('')
            b.setFixedSize(26,26)
            b.setAccessibleName('Couleur '+color)
            b.setToolTip(color)
            b.setStyleSheet(
                'QPushButton { background:'+color+';border:1px solid #74809B;'
                'border-radius:7px;padding:0; }'
                'QPushButton:hover { border:2px solid #FFFFFF; }'
            )
            b.clicked.connect(lambda checked=False,c=color:self.set_color(c))
            self.presets.addWidget(b)
            self.preset_buttons.append(b)
        self.presets.addStretch(1)
        outer.addLayout(self.presets)
        self.set_color(self._current,emit=False)

    def color(self) -> str:
        return self._current

    def set_color(self,value,*,emit=True):
        candidate=validate_color(str(value))
        if candidate is None:
            return False
        changed=candidate!=self._current
        self._current=candidate
        self._changing=True
        self.hex.setText(candidate)
        self.hex.setStyleSheet('border:1px solid #414761;')
        self.swatch.setStyleSheet(
            'QPushButton { background:'+candidate+';border:2px solid #ACA9C3;'
            'border-radius:9px;padding:0; }'
            'QPushButton:hover { border:2px solid #FFFFFF; }'
        )
        self.swatch.setToolTip(self.title+' : '+candidate)
        self._changing=False
        if emit and changed:
            self.color_changed.emit(candidate)
        return True

    def apply_hex(self):
        if self._changing:
            return
        if not self.set_color(self.hex.text()):
            self.hex.setText(self._current)
            self.hex.setStyleSheet('border:1px solid #ED8D9D;')
            self.hex.setToolTip('Valeur invalide : utilise #RRGGBB (exemple : #845CF7).')

    def open_dialog(self):
        selected=QColorDialog.getColor(QColor(self._current),self,'Couleur · '+self.title)
        if selected.isValid():
            self.set_color(selected.name().upper())
