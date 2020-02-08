import cv2
import argparse
import numpy as np
import colorsys
import math

WINDOW_WIDTH = 970
WINDOW_HEIGHT = 896

parser = argparse.ArgumentParser()
parser.add_argument('-x', required=True, type=int, dest='x', default=0)
parser.add_argument('-y', required=True, type=int, dest='y', default=0)
parser.add_argument('-d', '--direction', default='to', choices=['to', 'from'], dest='direction')
parser.add_argument('--width', required=True, type=int, dest='width')
parser.add_argument('--height', required=True, type=int, dest='height')
args = parser.parse_args()

CELLS_X = args.width
CELLS_Y = args.height

selected = [args.x + args.y * CELLS_Y]

heatmap = np.full((CELLS_X, CELLS_Y, 3), 0)

distance = np.load('distance_matrix.npy')

def distance_to_color(distance):
  # if distance == 0: return np.array([1, 1, 1])
  min_heat = cv2.getTrackbarPos('minheat', 'Heatmap')
  max_heat = cv2.getTrackbarPos('maxheat', 'Heatmap')
  heat_range = max_heat - min_heat
  out = colorsys.hsv_to_rgb(
    min(max(distance-min_heat, 0), heat_range) / ((heat_range)*1.5),
    1,
    1 - min(max(distance-min_heat, 0), heat_range) / (heat_range) / 2
  )
  # out = colorsys.hsv_to_rgb(math.log10(distance), 1, 1 - min(distance, 90) / 180)
  return np.array(out)

def extract_array(list_of_points, direction):
  global distance
  if direction == 'from':
    return np.average(distance[list_of_points, :], axis=0)
  else:
    return np.average(distance[:, list_of_points], axis=1)

def compute_heatmap(array):
  global CELLS_X, CELLS_Y, heatmap

  heatmap = np.empty((CELLS_X, CELLS_Y, 3))
  for x in range(CELLS_X):
    for y in range(CELLS_Y):
      heatmap[y, x, :] = distance_to_color(array[x + (CELLS_Y - y - 1)*CELLS_X])

  heatmap = cv2.resize(heatmap, (WINDOW_WIDTH, WINDOW_HEIGHT), interpolation=cv2.INTER_NEAREST)
  sofia = cv2.imread('sofia.jpg', flags=cv2.IMREAD_COLOR)
  heatmap = cv2.addWeighted(heatmap, 0.5, np.array(sofia, dtype=float)/255, 0.5, 0)

def on_click(event, x, y, flags, param):
  global WINDOW_WIDTH, WINDOW_HEIGHT, CELLS_X, CELLS_Y, selected
  if event == cv2.EVENT_LBUTTONDOWN:
    box_clicked_x = int(x / WINDOW_WIDTH * CELLS_X)
    box_clicked_y = int((WINDOW_HEIGHT - y) / WINDOW_HEIGHT * CELLS_Y)
    if flags & cv2.EVENT_FLAG_SHIFTKEY == cv2.EVENT_FLAG_SHIFTKEY:
      if box_clicked_x + box_clicked_y * CELLS_Y in selected:
        selected.remove(box_clicked_x + box_clicked_y * CELLS_Y)
      else:
        selected.append(box_clicked_x + box_clicked_y * CELLS_Y)
    else:
      selected = [box_clicked_x + box_clicked_y * CELLS_Y]
      
    compute_heatmap(extract_array(selected, args.direction))
    cv2.imshow('Heatmap', heatmap)
    
def on_trackbar_change(value):
  global selected, args, heatmap
  compute_heatmap(extract_array(selected, args.direction))
  cv2.imshow('Heatmap', heatmap)

if __name__ == '__main__':
  
  cv2.namedWindow('Heatmap', flags=cv2.WINDOW_AUTOSIZE)
  cv2.createTrackbar('minheat', 'Heatmap', 0, 300, on_trackbar_change)
  cv2.createTrackbar('maxheat', 'Heatmap', 90, 300, on_trackbar_change)
  cv2.setMouseCallback('Heatmap', on_click)
  
  compute_heatmap(extract_array(selected, args.direction))
  cv2.imshow('Heatmap', heatmap)

  cv2.waitKey()
  cv2.destroyAllWindows()
