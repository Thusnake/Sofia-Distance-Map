import sys
import colorsys
import numpy as np
from PyQt5 import QtWidgets as widgets
from PyQt5.QtGui import QIcon, QPixmap, QImage, QColor, QMouseEvent
from PyQt5 import QtCore

class DistanceMap(widgets.QGraphicsView):
  """
  Represents the heatmap of temporal distances.
  """
  
  def __init__(self, parent, hor_pixels, ver_pixels):
    super(DistanceMap, self).__init__(parent)
    
    self.min_heat = 0
    self.max_heat = 60
    
    self.hor_pixels = hor_pixels
    self.ver_pixels = ver_pixels
    
    self._scene = widgets.QGraphicsScene(self)
    self.setScene(self._scene)
    
    map_pixmap = QPixmap('sofia.jpg')
    self.map_image = self._scene.addPixmap(map_pixmap)
    
    heat_pixmap = QPixmap(self.map_image.pixmap().width(), self.map_image.pixmap().height())
    heat_pixmap.fill(QtCore.Qt.red)
    self.heat_image = self._scene.addPixmap(heat_pixmap)
    
    self.show()
    
  def setDistanceMap(self, distances):
    """
    Updates the heat colors of the distance map according to a two-dimensional 
    numpy array.
    """
    
    img = QImage(self.hor_pixels, self.ver_pixels, QImage.FormatRGB32)
    for x in range(self.hor_pixels):
      for y in range(self.ver_pixels):
        img.setPixel(x, y, self.distance_to_color(distances[x, y]).value())
    
    pixmap: QPixmap = QPixmap.fromImage(img)
    pixmap.scaled(self.map_image.pixmap().width(), self.map_image.pixmap().height())
    self.heat_image.setPixmap()
    
  def distance_to_color(self, distance) -> QColor:
    """
    Computes a QColor given some temporal distance value. Takes into account
    the current min_heat and max_heat.
    """
    
    heat_range = self.max_heat - self.min_heat
    out = QColor.fromHsvF(
      min(max(distance-min_heat, 0), heat_range) / ((heat_range)*1.5),
      1,
      1 - min(max(distance-min_heat, 0), heat_range) / (heat_range) / 2
    )
    return out
  
  def mousePressEvent(self, event: QMouseEvent):
    
    return super().mousePressEvent(self, event)
    
class App(widgets.QApplication):
  def __init__(self):
    super().__init__(sys.argv)
    
    self.style('Fusion')
    
    self.window = widgets.QWidget()
    self.layout = widgets.QHBoxLayout()
    
    # On the left - Distance map and heat adjustment controls
    self.left_layout = widgets.QVBoxLayout()
    self.dist_map_widget = DistanceMap(None, 100, 100)
    self.left_layout.addWidget(self.dist_map_widget)
    self.layout.addLayout(self.left_layout)
    
    # On the right - Region selection
    self.right_layout = widgets.QVBoxLayout()
    self.layout.addLayout(self.right_layout)
    

if __name__ == '__main__':
  app = widgets.QApplication(sys.argv)
  sys.exit(app.exec_())