"""Shared interactive slider: click anywhere, drag, hover preview, wheel safe."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider, QToolTip

class ClickJumpSlider(QSlider):
    """Move slider to any point along its track, preserving drag behavior."""
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self._jump_drag=False

    def value_at(self, point):
        option=QStyleOptionSlider()
        self.initStyleOption(option)
        groove=self.style().subControlRect(QStyle.CC_Slider,option,QStyle.SC_SliderGroove,self)
        handle=self.style().subControlRect(QStyle.CC_Slider,option,QStyle.SC_SliderHandle,self)
        if self.orientation()==Qt.Horizontal:
            origin=groove.x()+handle.width()/2
            span=max(1,groove.width()-handle.width())
            coordinate=round(point.x()-origin)
        else:
            origin=groove.y()+handle.height()/2
            span=max(1,groove.height()-handle.height())
            coordinate=round(point.y()-origin)
        return QStyle.sliderValueFromPosition(self.minimum(),self.maximum(),coordinate,span,option.upsideDown)

    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            self._jump_drag=True
            self.setSliderDown(True)
            self._jump_to(event.position().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def _jump_to(self,point):
        v=self.value_at(point)
        self.setSliderPosition(v)
        self.setValue(v)
        self.sliderMoved.emit(v)

    def mouseMoveEvent(self,event):
        if self._jump_drag and (event.buttons() & Qt.LeftButton):
            self._jump_to(event.position().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if self._jump_drag and event.button()==Qt.LeftButton:
            self._jump_to(event.position().toPoint())
            self._jump_drag=False
            self.setSliderDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self,event):
        # Specific parent classes may reroute wheel events to the settings pane.
        event.ignore()

class VideoSeekSlider(ClickJumpSlider):
    """In-player seek bar with exact timestamp tooltip at cursor location."""
    def mouseMoveEvent(self,event):
        super().mouseMoveEvent(event)
        if self.maximum()>0:
            v=self.value_at(event.position().toPoint())
            QToolTip.showText(event.globalPosition().toPoint(),
                              f'{v//60000:02d}:{(v//1000)%60:02d}',self)
    def leaveEvent(self,event):
        QToolTip.hideText()
        super().leaveEvent(event)
