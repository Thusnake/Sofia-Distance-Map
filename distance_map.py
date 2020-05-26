import sys
import colorsys
import numpy as np
import threading
from collections import defaultdict
from json import JSONDecoder
from typing import List, Callable, Dict, DefaultDict, Set
from nptyping import Array
from PyQt5 import QtWidgets as widgets
from PyQt5.QtGui import QIcon, QPixmap, QImage, QColor, QMouseEvent, QPen, QBrush, QFont
from PyQt5 import QtCore

HOR_PIXELS, VER_PIXELS = 100, 100
HOVER_TEXTBOX_PADDING = 5

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
    
    self.curr_distances = None
    self.onMouseClickHandler: Callable[[QMouseEvent], None] = None
    self.hoverTextHandler: Callable[[int, int], str] = None
    
    self._scene = widgets.QGraphicsScene(self)
    self.setScene(self._scene)
    self._scene.installEventFilter(self)
    
    map_pixmap = QPixmap('sofia.jpg')
    self.map_image: widgets.QGraphicsPixmapItem = self._scene.addPixmap(map_pixmap)
    self._scene.setSceneRect(0, 0, map_pixmap.width(), map_pixmap.height())
    
    heat_pixmap = QPixmap(self.map_image.pixmap().width(), self.map_image.pixmap().height())
    heat_pixmap.fill(QtCore.Qt.red)
    self.heat_image: widgets.QGraphicsPixmapItem = self._scene.addPixmap(heat_pixmap)
    self.heat_image.setAcceptHoverEvents(True)
    
    hover_rect_pen = QPen(QtCore.Qt.white, 2)
    self.hover_rect: widgets.QGraphicsRectItem = self._scene.addRect(0, 0, 0, 0, pen=hover_rect_pen)
    self.hover_rect.setVisible(False)
    
    self.hover_text: widgets.QGraphicsSimpleTextItem = self._scene.addSimpleText('')
    self.hover_text.setVisible(False)
    self.hover_text.setBrush(QBrush(QtCore.Qt.white))
    self.hover_text.setZValue(1000)
    
    self.hover_text_bg: widgets.QGraphicsRectItem = self._scene.addRect(0, 0, 0, 0, brush=QBrush(QtCore.Qt.black))
    self.hover_text_bg.setVisible(False)
    
    shdw_mask = QPixmap(self.map_image.pixmap().width(), self.map_image.pixmap().height())
    shdw_mask.fill(QtCore.Qt.black)
    self.shadow_mask: widgets.QGraphicsPixmapItem = self._scene.addPixmap(shdw_mask)
    self.shadow_mask.setOpacity(0.5)
    self.shadow_mask.setVisible(False)
    
    self.show()
    
  def updateDistances(self, distances):
    """
    Updates the heat colors of the distance map according to a two-dimensional 
    numpy array.
    """
    self.curr_distances = distances
    
    img = QImage(self.hor_pixels, self.ver_pixels, QImage.Format_RGBA8888)
    for x in range(self.hor_pixels):
      for y in range(self.ver_pixels):
        img.setPixelColor(x, y, self.distance_to_color(distances[int(x + (self.ver_pixels - y - 1) * self.hor_pixels)]))
    
    pixmap: QPixmap = QPixmap.fromImage(img)
    pixmap = pixmap.scaled(self.map_image.pixmap().width(), self.map_image.pixmap().height())
    self.heat_image.setPixmap(pixmap)
    
  def setMinHeat(self, new_min_heat):
    print(new_min_heat)
    self.min_heat = new_min_heat
    self.updateDistances(self.curr_distances)
  
  def setMaxHeat(self, new_max_heat):
    print(new_max_heat)
    self.max_heat = new_max_heat
    self.updateDistances(self.curr_distances)
    
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
  
  def windowToSquareX(self, x: float) -> int:
    return int(x / self._scene.width() * self.hor_pixels)
  
  def windowToSquareY(self, y: float) -> int:
    return int(y / self._scene.height() * self.ver_pixels)
  
  def windowToSquareYInv(self, y: float) -> int:
    return int((self._scene.height() - y - 1) / self._scene.height() * self.ver_pixels)
  
  def eventFilter(self, source, event):
    if source is self._scene:
      if event.type() == QtCore.QEvent.GraphicsSceneMouseRelease and\
         event.button() == QtCore.Qt.LeftButton:
        self.onMouseClickHandler(event.scenePos())
      elif event.type() == QtCore.QEvent.GraphicsSceneMouseMove:
        self.onMouseHover(event.scenePos())
    return widgets.QWidget.eventFilter(self, source, event)
  
  def setMouseClickHandler(self, call: Callable[[QMouseEvent], None]):
    self.onMouseClickHandler = call
  
  def setHoverTextHandler(self, call: Callable[[int, int], None]):
    self.hoverTextHandler = call
    
  def onMouseHover(self, pos: QMouseEvent):
    if pos.x() < 0 or pos.x() >= self._scene.width() or pos.y() < 0 or pos.y() >= self._scene.height():
      return
    
    self.hover_rect.setVisible(True)
    self.hover_rect.setRect(
      self.windowToSquareX(pos.x()) * self._scene.width() / self.hor_pixels,
      self.windowToSquareY(pos.y()) * self._scene.height() / self.ver_pixels,
      self._scene.width() / self.hor_pixels,
      self._scene.height() / self.ver_pixels
    )
    
    self.hover_text.setVisible(True)
    self.hover_text.setText(self.hoverTextHandler(
      self.windowToSquareX(pos.x()),
      self.windowToSquareYInv(pos.y())
    ))
    
    x_square_offset = 1 if pos.x() <= self._scene.width() // 2 else 0
    x_offset = -self.hover_text.boundingRect().width() if pos.x() > self._scene.width() // 2 else 0
    y_offset = -self.hover_text.boundingRect().height() if pos.y() > self._scene.height() // 2 else 0
    self.hover_text.setPos(
      (self.windowToSquareX(pos.x()) + x_square_offset) * self._scene.width() / self.hor_pixels + x_offset,
      self.windowToSquareY(pos.y()) * self._scene.height() / self.ver_pixels + y_offset
    )
    
    self.hover_text_bg.setVisible(True)
    self.hover_text_bg.setRect(
      self.hover_text.x() - HOVER_TEXTBOX_PADDING,
      self.hover_text.y() - HOVER_TEXTBOX_PADDING,
      self.hover_text.boundingRect().width() + HOVER_TEXTBOX_PADDING * 2,
      self.hover_text.boundingRect().height() + HOVER_TEXTBOX_PADDING * 2
    )
    
    self.hover_text_bg.setOpacity(0.5)
    
  def shadowMaskSquares(self, squares: List[int]):
    """
    Enables the shadow mask, highlighting only a given set of squares.
    """
    new_shadow_mask = QImage(self.map_image.pixmap().width(), self.map_image.pixmap().height(), QImage.Format_RGBA8888)
    new_shadow_mask.fill(QtCore.Qt.black)
    print('Shadow_mask size: %.2f, %.2f' % (new_shadow_mask.width(), new_shadow_mask.height()))
    
    square_width = self.map_image.boundingRect().width() / self.hor_pixels
    square_height = self.map_image.boundingRect().height() / self.ver_pixels
    for square_number in squares:
      sq_x, sq_y = square_number % self.hor_pixels, square_number // self.hor_pixels
      sq_y = self.ver_pixels - sq_y - 1 # Invert Y.
      window_x, window_y = sq_x * square_width, sq_y * square_height
      
      for x in range(int(window_x), min(int(window_x + square_width + 1), new_shadow_mask.width())):
        for y in range(int(window_y), min(int(window_y + square_height + 1), new_shadow_mask.height())):
          new_shadow_mask.setPixelColor(x, y, QtCore.Qt.transparent)
      
    self.shadow_mask.setPixmap(QPixmap.fromImage(new_shadow_mask))
    self.shadow_mask.setVisible(True)
  
  def clearShadowMask(self):
    """
    Removes the shadow mask.
    """
    self.shadow_mask.fill(QtCore.Qt.black)
    self.shadow_mask.setVisible(False)

class DistrictTableWidget(widgets.QTableWidget):
  rowEntered = QtCore.pyqtSignal(int)
  
  def __init__(self, rows: int, cols: int, parent=None):
    super().__init__(rows, cols, parent=parent)
    self.viewport().installEventFilter(self)
    self._last_index = QtCore.QPersistentModelIndex()
  
  def eventFilter(self, widget, event: QtCore.QEvent):
    if widget is self.viewport():
      index = self._last_index
      if event.type() == QtCore.QEvent.MouseMove:
        index = self.indexAt(event.pos())
      elif event.type() == QtCore.QEvent.Leave:
        index = QtCore.QModelIndex()
      
      if index != self._last_index:
        row = index.row()
        column = index.column()
        item = self.item(row, column)
        
        if item is not None:
          self.rowEntered.emit(row)

        self._last_index = QtCore.QPersistentModelIndex(index)
    
    return super(DistrictTableWidget, self).eventFilter(widget, event)

class NumericTableWidgetItem(widgets.QTableWidgetItem):
  def __init__(self, value: int):
    super().__init__(str(value))
  
  def __lt__(self, other):
    if isinstance(other, widgets.QTableWidgetItem):
      try:
        return float(self.data(QtCore.Qt.EditRole)) < float(other.data(QtCore.Qt.EditRole))
      except ValueError as e:
        print('Could not compare table item values')
        print(e)
    
    return super(NumericTableWidgetItem, self).__lt__(other)

class App(widgets.QApplication):
  def __init__(self):
    super().__init__(sys.argv)
    
    self.setStyle('Fusion')
    
    self.window = widgets.QWidget()
    self.layout = widgets.QHBoxLayout()
    
    # On the left - Distance map and heat adjustment controls
    self.left_layout = widgets.QVBoxLayout()
    
    self.dist_map_widget = DistanceMap(None, HOR_PIXELS, VER_PIXELS)
    self.dist_map_widget.setMouseClickHandler(self.onDistMapWidgetClicked)
    self.left_layout.addWidget(self.dist_map_widget)
    
    self.min_heat_slider = widgets.QSlider(QtCore.Qt.Horizontal)
    self.min_heat_slider.setMinimum(0)
    self.min_heat_slider.setMaximum(120)
    self.min_heat_slider.setValue(0)
    self.min_heat_slider.setTickPosition(widgets.QSlider.TicksBelow)
    self.min_heat_slider.setTickInterval(1)
    self.min_heat_slider.valueChanged.connect(self.onMinHeatChanged)
    self.left_layout.addWidget(self.min_heat_slider)
    
    self.max_heat_slider = widgets.QSlider(QtCore.Qt.Horizontal)
    self.max_heat_slider.setMinimum(0)
    self.max_heat_slider.setMaximum(120)
    self.max_heat_slider.setValue(60)
    self.max_heat_slider.setTickPosition(widgets.QSlider.TicksBelow)
    self.max_heat_slider.setTickInterval(1)
    self.max_heat_slider.valueChanged.connect(self.onMaxHeatChanged)
    self.left_layout.addWidget(self.max_heat_slider)
    
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
    
    # Load squares area affiliation.
    self.square_affiliation: DefaultDict[int, Set[str]] = defaultdict(lambda: set())
    self.regions_to_squares: DefaultDict[str, List[int]] = defaultdict(lambda: [])
    self.fetchSquareInfo()
    self.dist_map_widget.setHoverTextHandler(self.squareInfoToString)
    
    self.region_table_widget = DistrictTableWidget(len(self.regions_to_squares.keys()), 3)
    for i, region in enumerate(self.regions_to_squares.keys()):
      self.region_table_widget.setItem(i, 0, widgets.QTableWidgetItem(region))
      self.region_table_widget.setItem(i, 1, NumericTableWidgetItem(0))
      self.region_table_widget.setItem(i, 2, NumericTableWidgetItem(0))
    self.region_table_widget.setSortingEnabled(True)
    self.region_table_widget.setMouseTracking(True)
    self.region_table_widget.rowEntered.connect(self.onDistrictRowHover)
    self.right_layout.addWidget(self.region_table_widget)
    
    self.direction = 'to'
    self.origins = []
    
  def onDistanceMapLoaded(self, result):
    self.distance_map_raw = result
    print("Loaded!")
  
  def fetchSquareInfo(self):
    """
    Load all the prefetched information about the squares' regional affiliation.
    """
    
    with open('square_info.json', 'r') as file:
      decoder = JSONDecoder()
      square_info_json = decoder.decode(file.read())
      for square_number, info in square_info_json.items():
        if info == None:
          continue
        
        self.square_affiliation[int(square_number)].update(value for key, value in info.items())
        for key, value in info.items():
          self.regions_to_squares[value].append(int(square_number))
  
  def squareInfoToString(self, x: int, y: int) -> str:
    if self.square_affiliation == None:
      return ''
    return '\n'.join(list(self.square_affiliation[x + y * HOR_PIXELS]))
    
  def onMinHeatChanged(self, value):
    self.dist_map_widget.setMinHeat(value)
    self.max_heat_slider.setMinimum(value)
    
  def onMaxHeatChanged(self, value):
    self.dist_map_widget.setMaxHeat(value)
    self.min_heat_slider.setMaximum(value)
    
  def onDistMapWidgetClicked(self, pos: QMouseEvent):
    if pos.x() < 0 or pos.x() > self.dist_map_widget.scene().width()\
       or pos.y() < 0 or pos.y() > self.dist_map_widget.scene().height():
      return
  
    box_clicked_x = self.dist_map_widget.windowToSquareX(pos.x())
    box_clicked_y = self.dist_map_widget.windowToSquareYInv(pos.y())
    
    new_origin = int(box_clicked_x + box_clicked_y * self.dist_map_widget.hor_pixels)
    print(new_origin)
    self.setOrigins([new_origin])
  
  def setOrigins(self, origins: List[int]):
    self.origins = origins
    if self.direction == 'from':
      distances = np.max(self.distance_map_raw[self.origins, :], axis=0)
    else:
      distances = np.max(self.distance_map_raw[:, self.origins], axis=1)
    
    self.dist_map_widget.updateDistances(distances)
    
    for i, (region, squares) in enumerate(self.regions_to_squares.items()):
      self.region_table_widget.item(i, 0).setText(region)
      self.region_table_widget.item(i, 1).setText('%.2f' % np.average(distances[squares]))
      self.region_table_widget.item(i, 2).setText('%.2f' % np.median(distances[squares]))
      
  def onDistrictRowHover(self, row: int):
    district_name = self.region_table_widget.item(row, 0).text()
    print('District %d hovered - %s' % (row, district_name))
    self.dist_map_widget.shadowMaskSquares(self.regions_to_squares[district_name])
      
  def invertSquareNumber(self, sq_number: int) -> int:
    """
    Returns the vertically-mirrored square number.
    
    This is done by transforming the square number into x and y coordinates,
    flipping the y coordinate and transforming the new pair into a square number.
    """
    
    x, y = sq_number % HOR_PIXELS, sq_number // HOR_PIXELS
    y = VER_PIXELS - y - 1
    return x + y * HOR_PIXELS

if __name__ == '__main__':
  app = App()
  sys.exit(app.exec_())