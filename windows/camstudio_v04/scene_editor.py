"""Visual editor for live composite scenes in CamStudio Pro."""
from __future__ import annotations
import copy
import time
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from PySide6.QtCore import Qt,QTimer,QPointF,Signal
from PySide6.QtGui import QImage,QPixmap,QPainter,QColor,QPen
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QListWidget,
    QInputDialog,QFileDialog,QMessageBox,QLineEdit,QCheckBox,QColorDialog,
    QSlider,QFrame,
)

from .scene_engine import SceneStore,composite
from .controls import ClickJumpSlider
from .scene_colors import SceneColorPicker


def _button(text,action):
    b=QPushButton(text)
    b.clicked.connect(action)
    return b


class SceneCanvas(QLabel):
    selection_changed=Signal(str)
    modified=Signal()
    def __init__(self,editor):
        super().__init__('Aperçu de scène')
        self.editor=editor
        self.setFixedSize(704,396)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet('background:#0A0C16;border:1px solid #434663;border-radius:10px;')
        self.setMouseTracking(True)
        self._drag=None
        self._start=None
        self._start_pos=None
        self.setToolTip('Clic sur un texte ou une image pour sélectionner. Glisse pour déplacer.')

    def _canvas_pos(self,pos):
        return (max(0.,min(1.,pos.x()/max(1,self.width()))),
                max(0.,min(1.,pos.y()/max(1,self.height()))))

    def _hit(self,x,y):
        scene=self.editor.store.active()
        for layer in reversed(scene['layers']):
            if not layer.get('visible',True):
                continue
            lx,ly,ww=layer['x'],layer['y'],layer['width']
            if layer['kind']=='text':
                hh=max(.06,layer.get('font_size',34)/720*1.6)
            else:
                from .scene_engine import _cached_image
                path=Path(layer.get('path',''))
                try:
                    img=_cached_image(str(path),path.stat().st_mtime_ns)
                    hh=ww*img.height()/max(1,img.width())*16/9 if img else ww
                except OSError:
                    hh=ww*.55
            if lx<=x<=lx+ww and ly<=y<=ly+hh:
                return layer['id']
        return None

    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            x,y=self._canvas_pos(event.position())
            layer_id=self._hit(x,y)
            self.editor.select_layer(layer_id)
            if layer_id:
                layer=self.editor.active_layer()
                self._drag=layer_id
                self._start=(x,y)
                self._start_pos=(layer['x'],layer['y'])
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self._drag is not None and self._start is not None and (event.buttons()&Qt.LeftButton):
            layer=self.editor.active_layer()
            if layer is not None and layer['id']==self._drag:
                x,y=self._canvas_pos(event.position())
                layer['x']=max(0.,min(.98,self._start_pos[0]+x-self._start[0]))
                layer['y']=max(0.,min(.98,self._start_pos[1]+y-self._start[1]))
                self.editor.render_preview(force=True)
                self.modified.emit()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if self._drag is not None and event.button()==Qt.LeftButton:
            self._drag=None
            self.editor.store.save()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def show_frame(self,frame):
        h,w=frame.shape[:2]
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        pic=QImage(rgb.data,w,h,rgb.strides[0],QImage.Format_RGB888).copy()
        p=QPixmap.fromImage(pic).scaled(self.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation)
        if self.editor.selected_layer:
            painter=QPainter(p)
            painter.setPen(QPen(QColor('#C9A7FF'),2,Qt.DashLine))
            layer=self.editor.active_layer()
            if layer:
                x,y=layer['x']*p.width(),layer['y']*p.height()
                width=layer['width']*p.width()
                height=layer.get('font_size',30)*p.height()/720*1.55 if layer['kind']=='text' else width*.58
                painter.drawRect(int(x),int(y),int(width),int(max(16,height)))
            painter.end()
        self.setPixmap(p)


class SceneEditor(QWidget):
    def __init__(self,studio,parent=None):
        super().__init__(parent)
        self.studio=studio
        self.store=studio.scenes
        self.selected_layer=None
        self._updating=False
        outer=QVBoxLayout(self)
        outer.setContentsMargins(0,2,0,2)
        outer.setSpacing(10)
        bar=QHBoxLayout()
        bar.addWidget(QLabel('Scène active :'))
        self.choose=QComboBox()
        self.choose.setMinimumWidth(190)
        self.choose.currentIndexChanged.connect(self._scene_chosen)
        bar.addWidget(self.choose)
        bar.addWidget(_button('Nouvelle scène',self.add_scene))
        bar.addWidget(_button('Renommer',self.rename_scene))
        bar.addWidget(_button('Dupliquer',self.duplicate_scene))
        bar.addWidget(_button('Supprimer',self.delete_scene))
        bar.addStretch(1)
        outer.addLayout(bar)
        self.canvas=SceneCanvas(self)
        outer.addWidget(self.canvas,alignment=Qt.AlignLeft)
        help_text=QLabel('Caméra + textes + images : l’aperçu correspond à la scène envoyée aux sorties. '
                         'Clique un élément et déplace-le directement sur l’image.')
        help_text.setWordWrap(True)
        outer.addWidget(help_text)
        overlays=QHBoxLayout()
        overlays.addWidget(_button('Ajouter un texte',self.add_text))
        overlays.addWidget(_button('Ajouter une image',self.add_image))
        overlays.addWidget(_button('Supprimer l’élément',self.remove_layer))
        outer.addLayout(overlays)
        row=QHBoxLayout()
        elements=QVBoxLayout()
        elements.addWidget(QLabel('Éléments de la scène (du bas vers le haut)'))
        self.layer_list=QListWidget()
        self.layer_list.setMaximumHeight(155)
        self.layer_list.currentRowChanged.connect(self._layer_selected)
        elements.addWidget(self.layer_list)
        order=QHBoxLayout()
        order.addWidget(_button('↑ Devant',lambda:self.reorder_layer(1)))
        order.addWidget(_button('↓ Derrière',lambda:self.reorder_layer(-1)))
        elements.addLayout(order)
        row.addLayout(elements,1)
        attrs=QVBoxLayout()
        attrs.addWidget(QLabel('Propriétés de l’élément sélectionné'))
        self.name_edit=QLineEdit()
        self.name_edit.setPlaceholderText('Texte affiché')
        self.name_edit.editingFinished.connect(self.update_text)
        attrs.addWidget(self.name_edit)
        self.visible=QCheckBox('Visible')
        self.visible.toggled.connect(self._visibility)
        attrs.addWidget(self.visible)
        attrs.addWidget(QLabel('Opacité'))
        self.opacity=ClickJumpSlider(Qt.Horizontal)
        self.opacity.setRange(0,100)
        self.opacity.valueChanged.connect(self._opacity)
        attrs.addWidget(self.opacity)
        attrs.addWidget(QLabel('Taille du texte / largeur de l’image'))
        self.size_slider=ClickJumpSlider(Qt.Horizontal)
        self.size_slider.setRange(10,100)
        self.size_slider.valueChanged.connect(self._size_changed)
        attrs.addWidget(self.size_slider)
        self.text_color = SceneColorPicker('Couleur du texte','#FFFFFF')
        self.text_color.color_changed.connect(self._set_text_color)
        attrs.addWidget(self.text_color)
        row.addLayout(attrs,1)
        outer.addLayout(row)
        lower=QHBoxLayout()
        lower.addWidget(QLabel('Arrière-plan :'))
        self.background=QComboBox()
        self.background.addItems(['Caméra du téléphone','Couleur unie'])
        self.background.currentIndexChanged.connect(self._background)
        lower.addWidget(self.background)
        lower.addWidget(QLabel('Transition :'))
        self.transition=QComboBox()
        self.transition.addItems(['Fondu','Aucune'])
        self.transition.currentTextChanged.connect(self._transition)
        lower.addWidget(self.transition)
        lower.addWidget(QLabel('Durée du fondu :'))
        self.duration=QComboBox()
        self.duration.addItems(['150 ms','260 ms','500 ms','800 ms'])
        self.duration.currentTextChanged.connect(self._duration)
        lower.addWidget(self.duration)
        # Make background color controls visible above the large scene preview.
        outer.insertLayout(1,lower)
        self.background_color = SceneColorPicker('Couleur de fond de cette scène','#15112D')
        self.background_color.color_changed.connect(self._set_background_color)
        outer.insertWidget(2,self.background_color)
        self.background_color_help = QLabel(
            'Choisir une couleur de fond active automatiquement « Couleur unie ». '
            'Pour revoir la caméra, sélectionne « Caméra du téléphone ».'
        )
        self.background_color_help.setWordWrap(True)
        self.background_color_help.setStyleSheet('color:#A9AFC9;')
        outer.insertWidget(3,self.background_color_help)
        note=QLabel('Les scènes sont sauvegardées uniquement sur ce PC. '
                    'Les sources caméra supplémentaires seront intégrées séparément.')
        note.setWordWrap(True)
        outer.addWidget(note)
        self.reload()
        self._preview_tick=QTimer(self)
        self._preview_tick.setInterval(160)
        self._preview_tick.timeout.connect(self.render_preview)
        self._preview_tick.start()

    def reload(self):
        self._updating=True
        self.choose.clear()
        for scene in self.store.data['scenes']:
            self.choose.addItem(scene['name'],scene['id'])
        ix=self.choose.findData(self.store.data['active_id'])
        self.choose.setCurrentIndex(ix if ix>=0 else 0)
        self.transition.setCurrentText(self.store.data['transition'])
        self.duration.setCurrentText(f"{self.store.data['transition_ms']} ms")
        if self.duration.findText(self.duration.currentText())<0:
            self.duration.addItem(self.duration.currentText())
        self._updating=False
        self._load_layers()
        self.render_preview(force=True)

    def _scene_chosen(self,index):
        if self._updating or index<0:
            return
        self.store.activate(self.choose.itemData(index))
        self.selected_layer=None
        self._load_layers()
        self.render_preview(force=True)

    def _load_layers(self):
        self._updating=True
        self.layer_list.clear()
        scene=self.store.active()
        for layer in scene['layers']:
            self.layer_list.addItem(('T  ' + layer['text'][:22]) if layer['kind']=='text' else
                                   ('▧  ' + Path(layer['path']).name[:28]))
        current=next((i for i,layer in enumerate(scene['layers'])
                      if layer['id']==self.selected_layer),-1)
        self.layer_list.setCurrentRow(current)
        self.background.setCurrentIndex(1 if scene['background']=='color' else 0)
        self.background_color.set_color(scene.get('background_color','#15112D'),emit=False)
        self._updating=False
        self._load_properties()

    def _layer_selected(self,index):
        if self._updating:return
        layers=self.store.active()['layers']
        self.selected_layer=layers[index]['id'] if 0<=index<len(layers) else None
        self._load_properties()
        self.render_preview(force=True)

    def select_layer(self,layer_id):
        self.selected_layer=layer_id
        self._load_layers()

    def active_layer(self):
        return next((l for l in self.store.active()['layers'] if l['id']==self.selected_layer),None)

    def _load_properties(self):
        self._updating=True
        item=self.active_layer()
        for w in (self.name_edit,self.visible,self.opacity,self.size_slider):
            w.setEnabled(item is not None)
        is_text = item is not None and item['kind']=='text'
        self.text_color.setVisible(is_text)
        self.text_color.setEnabled(is_text)
        if is_text:
            self.text_color.set_color(item.get('color','#FFFFFF'),emit=False)
        if item:
            self.name_edit.setVisible(is_text)
            self.name_edit.setText(item.get('text',''))
            self.visible.setChecked(item['visible'])
            self.opacity.setValue(round(item['opacity']*100))
            self.size_slider.setValue(max(10,min(100,
                   round(item['font_size'] if item['kind']=='text' else item['width']*100))))
        else:
            self.name_edit.setVisible(False)
        self._updating=False

    def add_scene(self):
        text,ok=QInputDialog.getText(self,'Nouvelle scène','Nom de la scène :')
        if ok and text.strip():
            item=self.store.add(text.strip())
            self.store.activate(item['id'])
            self.selected_layer=None
            self.reload()

    def rename_scene(self):
        item=self.store.active()
        text,ok=QInputDialog.getText(self,'Renommer la scène','Nom :',text=item['name'])
        if ok and text.strip():
            item['name']=text.strip()[:55]
            self.store.save();self.reload()

    def duplicate_scene(self):
        src=copy.deepcopy(self.store.active())
        src['id']=uuid4().hex[:10]
        src['name']=(src['name']+' (copie)')[:55]
        self.store.data['scenes'].append(src)
        self.store.save();self.store.activate(src['id'])
        self.selected_layer=None;self.reload()

    def delete_scene(self):
        item=self.store.active()
        if len(self.store.data['scenes'])<=1:return
        answer=QMessageBox.question(self,'Supprimer la scène',
                f'Supprimer « {item["name"]} » ? Les vidéos déjà enregistrées sont conservées.')
        if answer==QMessageBox.Yes:
            self.store.remove(item['id']);self.selected_layer=None;self.reload()

    def add_text(self):
        text,ok=QInputDialog.getText(self,'Ajouter du texte','Texte à afficher :',text='Mon titre')
        if not ok or not text.strip():return
        layer={'id':uuid4().hex[:10],'kind':'text','text':text[:250],'x':.12,'y':.12,
               'width':.6,'font_size':43,'color':'#FFFFFF','opacity':1.,'visible':True}
        self.store.active()['layers'].append(layer)
        self.selected_layer=layer['id']
        self.store.save();self._load_layers();self.render_preview(force=True)

    def add_image(self):
        path,_=QFileDialog.getOpenFileName(self,'Choisir une image',str(Path.home()/'Pictures'),
                                  'Images (*.png *.jpg *.jpeg *.webp)')
        if not path:return
        img=QImage(path)
        if img.isNull():
            QMessageBox.warning(self,'Image','Impossible de lire ce fichier.')
            return
        layer={'id':uuid4().hex[:10],'kind':'image','path':path,'x':.12,'y':.12,
               'width':.3,'opacity':1.,'visible':True}
        self.store.active()['layers'].append(layer)
        self.selected_layer=layer['id']
        self.store.save();self._load_layers();self.render_preview(force=True)

    def remove_layer(self):
        if self.selected_layer is None:return
        scene=self.store.active()
        scene['layers']=[v for v in scene['layers'] if v['id']!=self.selected_layer]
        self.selected_layer=None
        self.store.save();self._load_layers();self.render_preview(force=True)

    def reorder_layer(self,delta):
        scene=self.store.active();layers=scene['layers']
        index=next((i for i,v in enumerate(layers) if v['id']==self.selected_layer),-1)
        target=index+delta
        if index<0 or target<0 or target>=len(layers):return
        layers[index],layers[target]=layers[target],layers[index]
        self.store.save();self._load_layers();self.render_preview(force=True)

    def _commit(self):
        if not self._updating:
            self.store.save()
            self.render_preview(force=True)

    def update_text(self):
        item=self.active_layer()
        if item and item['kind']=='text':
            item['text']=self.name_edit.text()[:250]
            self._commit();self._load_layers()

    def _visibility(self,value):
        item=self.active_layer()
        if item and not self._updating:
            item['visible']=bool(value);self._commit()

    def _opacity(self,value):
        item=self.active_layer()
        if item and not self._updating:
            item['opacity']=value/100;self._commit()

    def _size_changed(self,value):
        item=self.active_layer()
        if item and not self._updating:
            if item['kind']=='text':item['font_size']=int(value)
            else:item['width']=value/100
            self._commit()

    def _set_text_color(self,color):
        item=self.active_layer()
        if item and item['kind']=='text' and not self._updating:
            item['color']=color
            self._commit()

    def _set_background_color(self,color):
        if self._updating:
            return
        scene=self.store.active()
        scene['background_color']=color
        scene['background']='color'
        self._updating=True
        self.background.setCurrentIndex(1)
        self._updating=False
        self._commit()

    def pick_color(self):
        # Compatibility for older calls from plugins or shortcuts.
        if self.active_layer() and self.active_layer()['kind']=='text':
            self.text_color.open_dialog()

    def _background(self,index):
        if self._updating:return
        self.store.active()['background']='color' if index==1 else 'camera'
        self._commit()

    def _transition(self,value):
        if self._updating:return
        self.store.data['transition']=value
        self.store.save()

    def _duration(self,value):
        if self._updating:return
        try:ms=int(value.split()[0])
        except (ValueError,IndexError):return
        self.store.data['transition_ms']=ms
        self.store.save()

    def render_preview(self,force=False):
        if not force and not self.isVisible():return
        raw=getattr(self.studio,'last_raw_frame',None)
        if raw is None:
            frame=np.zeros((360,640,3),dtype=np.uint8)
            frame[:]=(20,14,11)
        else:
            from processor import process_frame
            frame=process_frame(raw,self.studio.settings,640,360)
        # Show edited active scene without re-triggering crossfades for each preview.
        scene=self.store.active()
        self.canvas.show_frame(composite(frame,(scene,None,1.)))
