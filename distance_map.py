import sys
import colorsys
import numpy as np
import threading
from typing import List, Callable
from PyQt5 import QtWidgets as widgets
from PyQt5.QtGui import QIcon, QPixmap, QImage, QColor, QMouseEvent
from PyQt5 import QtCore

class DistanceMap(widgets.QGraphicsView):
  """
  Represents the heatmap of temporal distances.
  """
  
  def __init__(self, parent, hor_pixels: int, ver_pixels: int):
    super(DistanceMap, self).__init__(parent)
    
    self.min_heat = 0
    self.max_heat = 60
    
    self.parent = parent
    self.hor_pixels = hor_pixels
    self.ver_pixels = ver_pixels
    
    self.onMouseClickHandler: function = None
    
    self._scene = widgets.QGraphicsScene(self)
    self.setScene(self._scene)
    self._scene.installEventFilter(self)
    
    map_pixmap = QPixmap('sofia.jpg')
    self.map_image = self._scene.addPixmap(map_pixmap)
    
    heat_pixmap = QPixmap(self.map_image.pixmap().width(), self.map_image.pixmap().height())
    heat_pixmap.fill(QtCore.Qt.red)
    self.heat_image = self._scene.addPixmap(heat_pixmap)
    
    self.show()
    
  def updateDistances(self, distances):
    """
    Updates the heat colors of the distance map according to a two-dimensional 
    numpy array.
    """
    
    img = QImage(self.hor_pixels, self.ver_pixels, QImage.Format_RGBA8888)
    for x in range(self.hor_pixels):
      for y in range(self.ver_pixels):
        img.setPixelColor(x, y, self.distance_to_color(distances[int(x + (self.ver_pixels - y - 1) * self.hor_pixels)]))
    
    pixmap: QPixmap = QPixmap.fromImage(img)
    pixmap = pixmap.scaled(self.map_image.pixmap().width(), self.map_image.pixmap().height())
    self.heat_image.setPixmap(pixmap)
    
  def distance_to_color(self, distance) -> QColor:
    """
    Computes a QColor given some temporal distance value. Takes into account
    the current min_heat and max_heat.
    """
    
    heat_range = self.max_heat - self.min_heat
    out = QColor.fromHsvF(
      min(max(distance-self.min_heat, 0), heat_range) / ((heat_range)*1.5),
      1,
      1 - min(max(distance-self.min_heat, 0), heat_range) / (heat_range) / 2,
      0.5
    )
    return out
  
  def eventFilter(self, source, event):
    if (source is self._scene and
        event.type() == QtCore.QEvent.GraphicsSceneMouseRelease and
        event.button() == QtCore.Qt.LeftButton):
      pos = event.scenePos()
      print('x=%0.01f,y=%0.01f' % (pos.x(), pos.y()))
      self.onMouseClickHandler(pos)
    return widgets.QWidget.eventFilter(self, source, event)
  
  def setMouseClickHandler(self, call: Callable[[QMouseEvent], None]):
    self.onMouseClickHandler = call
    
class App(widgets.QApplication):
  def __init__(self):
    super().__init__(sys.argv)
    
    HOR_PIXELS, VER_PIXELS = 100, 100
    
    self.setStyle('Fusion')
    
    self.window = widgets.QWidget()
    self.layout = widgets.QHBoxLayout()
    
    # On the left - Distance map and heat adjustment controls
    self.left_layout = widgets.QVBoxLayout()
    self.dist_map_widget = DistanceMap(None, HOR_PIXELS, VER_PIXELS)
    self.dist_map_widget.setMouseClickHandler(self.onDistMapWidgetClicked)
    
    self.left_layout.addWidget(self.dist_map_widget)
    self.layout.addLayout(self.left_layout)
    
    # On the right - Region selection
    self.right_layout = widgets.QVBoxLayout()
    self.layout.addLayout(self.right_layout)
    
    self.window.setLayout(self.layout)
    self.window.show()
    
    # Load distance map from file asynchronously.
    self.distance_map_raw: NpzFile = None
    threading.Thread(
      target=lambda: self.onDistanceMapLoaded(np.load('distance_matrix.npy')),
      daemon=True
    ).start()
    
    self.direction = 'to'
    self.origins = []
    
  def onDistanceMapLoaded(self, result):
    self.distance_map_raw = result
    print("Loaded!")
    
  def onDistMapWidgetClicked(self, pos: QMouseEvent):
    if pos.x() < 0 or pos.x() > self.dist_map_widget.scene().width()\
       or pos.y() < 0 or pos.y() > self.dist_map_widget.scene().height():
      return
  
    box_clicked_x = int(pos.x() / self.dist_map_widget.scene().width() * self.dist_map_widget.hor_pixels)
    box_clicked_y = int((self.dist_map_widget.scene().height() - pos.y()) / self.dist_map_widget.scene().height() * self.dist_map_widget.ver_pixels)
    
    new_origin = int(box_clicked_x + box_clicked_y * self.dist_map_widget.hor_pixels)
    print(new_origin)
    self.setOrigins([new_origin])
  
  def setOrigins(self, origins: List[int]):
    self.origins = origins
    if self.direction == 'from':
      self.dist_map_widget.updateDistances(np.max(self.distance_map_raw[self.origins, :], axis=0))
    else:
      self.dist_map_widget.updateDistances(np.max(self.distance_map_raw[:, self.origins], axis=1))

if __name__ == '__main__':
  app = App()
  sys.exit(app.exec_())