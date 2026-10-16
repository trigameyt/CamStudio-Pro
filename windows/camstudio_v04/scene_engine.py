"""CamStudio Pro scene compositing (local, no cloud).

A scene combines exactly one live phone-camera background or a solid-color
background with optional text/image sources. Qt paints an independent QImage,
so it can run in the camera's existing one-worker processing pool.
"""
from __future__ import annotations

import copy
import json
import os
import time
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

SCHEMA = 1
BASE = {
    'version': SCHEMA,
    'active_id': 'camera',
    'transition': 'Fondu',
    'transition_ms': 260,
    'scenes': [
        {'id':'camera','name':'Caméra','background':'camera','background_color':'#101321','layers':[]},
        {'id':'title','name':'Facecam + titre','background':'camera','background_color':'#101321',
         'layers':[{'id':'title-line','kind':'text','text':'CamStudio Pro',
                    'x':.055,'y':.055,'width':.55,'font_size':37,
                    'color':'#FFFFFF','opacity':1.,'visible':True}]},
        {'id':'standby','name':'Écran d’attente','background':'color','background_color':'#15112D',
         'layers':[{'id':'standby-text','kind':'text','text':'De retour bientôt',
                    'x':.20,'y':.41,'width':.75,'font_size':62,
                    'color':'#FFFFFF','opacity':1.,'visible':True}]},
    ],
}


def storage_path(base=None):
    return Path(base) if base else Path(os.getenv('APPDATA',str(Path.home()))) / 'CamStudioPro' / 'scenes.json'


def _sanitize_layer(raw):
    if not isinstance(raw,dict) or raw.get('kind') not in ('text','image'):
        return None
    layer={
        'id':str(raw.get('id','') or uuid4().hex[:10])[:50],
        'kind':raw['kind'],
        'x':max(0.,min(.95,float(raw.get('x',.12)))),
        'y':max(0.,min(.95,float(raw.get('y',.18)))),
        'width':max(.05,min(1.,float(raw.get('width',.4)))),
        'opacity':max(0.,min(1.,float(raw.get('opacity',1.)))),
        'visible':bool(raw.get('visible',True)),
    }
    if layer['kind']=='text':
        layer.update(text=str(raw.get('text','Titre'))[:250],
                     font_size=max(12,min(150,int(raw.get('font_size',40)))),
                     color=str(raw.get('color','#FFFFFF'))[:20])
    else:
        layer.update(path=str(raw.get('path',''))[:2048])
    return layer


def _sanitize_scene(s):
    if not isinstance(s,dict):
        return None
    return {
        'id':str(s.get('id') or uuid4().hex[:10])[:50],
        'name':str(s.get('name','Scène'))[:55],
        'background':'color' if s.get('background')=='color' else 'camera',
        'background_color':str(s.get('background_color','#15112D'))[:20],
        'layers':[v for item in s.get('layers',[])[:24] if (v:=_sanitize_layer(item))],
    }


def normalize(raw):
    if not isinstance(raw,dict):
        return copy.deepcopy(BASE)
    scenes=[s for item in raw.get('scenes',[])[:40] if (s:=_sanitize_scene(item))]
    if not scenes:
        scenes=copy.deepcopy(BASE['scenes'])
    ids=set()
    for scene in scenes:
        if scene['id'] in ids:
            scene['id']=uuid4().hex[:10]
        ids.add(scene['id'])
    transition=raw.get('transition','Fondu')
    return {
        'version':SCHEMA,
        'active_id':raw.get('active_id') if raw.get('active_id') in ids else scenes[0]['id'],
        'transition':transition if transition in ('Fondu','Aucune') else 'Fondu',
        'transition_ms':max(0,min(1200,int(raw.get('transition_ms',260)))),
        'scenes':scenes,
    }


class SceneStore:
    def __init__(self,path=None):
        self.path=storage_path(path)
        try:
            self.data=normalize(json.loads(self.path.read_text('utf-8')))
        except (OSError,ValueError,TypeError):
            self.data=copy.deepcopy(BASE)
        self._from=None
        self._transition_started=0.

    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        temp.replace(self.path)

    def active(self):
        return next((s for s in self.data['scenes'] if s['id']==self.data['active_id']),self.data['scenes'][0])

    def get(self,scene_id):
        return next((s for s in self.data['scenes'] if s['id']==scene_id),None)

    def activate(self,scene_id):
        nxt=self.get(scene_id)
        if nxt is None or nxt['id']==self.data['active_id']:
            return False
        self._from=copy.deepcopy(self.active())
        self._transition_started=time.monotonic()
        self.data['active_id']=scene_id
        self.save()
        return True

    def add(self,name='Nouvelle scène'):
        scene={'id':uuid4().hex[:10],'name':name[:55],'background':'camera',
               'background_color':'#15112D','layers':[]}
        self.data['scenes'].append(scene)
        self.save()
        return scene

    def remove(self,scene_id):
        if len(self.data['scenes'])<=1:
            return False
        before=len(self.data['scenes'])
        self.data['scenes']=[s for s in self.data['scenes'] if s['id']!=scene_id]
        if len(self.data['scenes'])==before:
            return False
        if self.data['active_id']==scene_id:
            self.data['active_id']=self.data['scenes'][0]['id']
            self._from=None
        self.save()
        return True

    def snapshot(self):
        scene=copy.deepcopy(self.active())
        elapsed=(time.monotonic()-self._transition_started)*1000
        ms=self.data['transition_ms']
        fading=self._from is not None and self.data['transition']=='Fondu' and ms>0 and elapsed<ms
        previous=copy.deepcopy(self._from) if fading else None
        if not fading:self._from=None
        return (scene,previous,max(0.,min(1.,elapsed/ms if ms else 1.)))


@lru_cache(maxsize=16)
def _cached_image(path,modified):
    image=QImage(path)
    return image if not image.isNull() else None


def _paint_scene(frame, scene):
    h,w=frame.shape[:2]
    # ARGB32 on little-endian Windows uses BGRA byte order, compatible with cv2.
    bgra=cv2.cvtColor(frame,cv2.COLOR_BGR2BGRA)
    qimg=QImage(bgra.data,w,h,bgra.strides[0],QImage.Format_ARGB32)
    painter=QPainter(qimg)
    painter.setRenderHint(QPainter.Antialiasing,True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform,True)
    if scene['background']=='color':
        painter.fillRect(0,0,w,h,QColor(scene['background_color']))
    for layer in scene.get('layers',[]):
        if not layer.get('visible',True) or not layer.get('opacity',1):
            continue
        painter.save()
        painter.setOpacity(layer.get('opacity',1))
        x,y=layer['x']*w,layer['y']*h
        width=layer['width']*w
        if layer['kind']=='image':
            path=Path(layer.get('path',''))
            try:
                if not path.is_file():
                    continue
                image=_cached_image(str(path),path.stat().st_mtime_ns)
            except OSError:
                painter.restore()
                continue
            if image:
                height=width*image.height()/max(1,image.width())
                painter.drawImage(QRectF(x,y,width,height),image)
        elif layer['kind']=='text':
            font=QFont('Segoe UI')
            font.setPixelSize(max(7,round(layer['font_size']*h/720)))
            font.setWeight(QFont.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor(layer.get('color','#FFFFFF'))))
            # Text width is a bounded rectangle; no unexpected overflow.
            painter.drawText(QRectF(x,y,width,max(20,h-y)),Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,layer['text'])
        painter.restore()
    painter.end()
    return np.ascontiguousarray(bgra[:,:,:3])


def composite(frame, snapshot):
    """Overlay scene on a processed BGR frame; crossfade when switching scenes."""
    current,previous,progress=snapshot
    result=_paint_scene(frame,current)
    if previous is not None:
        earlier=_paint_scene(frame,previous)
        result=cv2.addWeighted(earlier,1-progress,result,progress,0)
    return result


def process_with_scene(frame,settings,width,height,snapshot):
    from processor import process_frame
    return composite(process_frame(frame,settings,width,height),snapshot)
