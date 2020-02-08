import argparse
import json
import numpy as np
import math
import networkx

parser = argparse.ArgumentParser()
parser.add_argument('--width', default=100, type=int, dest='width')
parser.add_argument('--height', default=100, type=int, dest='height')
args = parser.parse_args()

# Load required files.
with open('routes.txt', 'r') as file:
  routes = json.load(file)
  
with open('stops-bg.json', 'r', encoding='utf8') as file:
  stations = json.load(file)

# Initialize adjacency matrix.
MATRIX_LEN = args.width * args.height + len(stations) + np.sum([len(route['stops']) for route in routes])
# adj_matrix = np.full((MATRIX_LEN, MATRIX_LEN), np.inf)
graph = networkx.DiGraph()
graph.add_nodes_from(range(MATRIX_LEN))
print('Matrix initialized...')

# Map station numbers, cells and routes to matrix indices.
station_to_node = {station['c']: index + args.width * args.height for index, station in enumerate(stations)}

def cell_to_node(x, y):
  return y * args.width + x

stop_index = 0
for route in routes:
  for stop in route['stops']:
    stop.append(stop_index)
    stop_index += 1

def stop_to_node(stop):
  return stop[2] + args.width * args.height + len(stations)

print('Mappings complete...')

# Connect adjacent map cells (walking distance).
EASTMOST_LAT = 23.19
WESTMOST_LAT = 23.47
NORTHMOST_LON = 42.79
SOUTHMOST_LON = 42.60

COVER_LAT = abs(EASTMOST_LAT - WESTMOST_LAT)
COVER_LON = abs(NORTHMOST_LON - SOUTHMOST_LON)

DEGREE_OF_LAT_IN_KM = 85
DEGREE_OF_LON_IN_KM = 111

CELL_WIDTH = COVER_LAT / args.width * DEGREE_OF_LAT_IN_KM
CELL_HEIGHT = COVER_LON / args.height * DEGREE_OF_LON_IN_KM

WALKING_SPEED_KMH = 4.5

for x in range(args.width):
  for y in range(args.height):
    if x > 0:
      graph.add_edge(cell_to_node(x, y), cell_to_node(x-1, y), weight = CELL_WIDTH / WALKING_SPEED_KMH * 60)
    if x < args.width-1:
      graph.add_edge(cell_to_node(x, y), cell_to_node(x+1, y), weight = CELL_WIDTH / WALKING_SPEED_KMH * 60)
    if y > 0:
      graph.add_edge(cell_to_node(x, y), cell_to_node(x, y-1), weight = CELL_HEIGHT / WALKING_SPEED_KMH * 60)
    if y < args.height-1:
      graph.add_edge(cell_to_node(x, y), cell_to_node(x, y+1), weight = CELL_HEIGHT / WALKING_SPEED_KMH * 60)

print('Walking distance done...')

# Connect cells to stations within them (instant).
for station in stations:
  if station['x'] > EASTMOST_LAT and station['x'] < WESTMOST_LAT and station['y'] > SOUTHMOST_LON and station['y'] < NORTHMOST_LON:
    cell_x = math.floor((station['x'] - EASTMOST_LAT) / COVER_LAT * args.width)
    cell_y = math.floor((station['y'] - SOUTHMOST_LON) / COVER_LON * args.height)
    graph.add_edge(cell_to_node(cell_x, cell_y), station_to_node[station['c']], weight = 0)
    graph.add_edge(station_to_node[station['c']], cell_to_node(cell_x, cell_y), weight = 0)

print('Station to cell mapping done...')

# Connect stations to routes (waiting time).
for route in routes:
  for stop in route['stops']:
    graph.add_edge(station_to_node[stop[1]], stop_to_node(stop), weight = route['median_wait'] / 2) # Bus waiting time (divide by 2 for avg. waiting time).
    graph.add_edge(stop_to_node(stop), station_to_node[stop[1]], weight = 0) # Instantly get off.
  
print('Station to route mapping done...')  

# Connect stations to stations (bus travel time).
for route in routes:
  for stop_from, stop_to in zip(route['stops'][:-1], route['stops'][1:]):
    if stop_from[0] == '***':
      delta = np.average(list(map(int, stop_to[0].split('-'))))
    else:
      delta = np.average(list(map(int, stop_to[0].split('-')))) - np.average(list(map(int, stop_from[0].split('-'))))
    
    graph.add_edge(stop_to_node(stop_from), stop_to_node(stop_to), weight = delta)

print('Connecting routes done...')

# Perform Floyd-Warshall on the graph to get the transitive closure.
# ALL_OPERATIONS = int(MATRIX_LEN) ** 3
# for k in range(MATRIX_LEN):
#   for i in range(MATRIX_LEN):
#     if adj_matrix[i][k] == np.inf: continue
#     for j in range(MATRIX_LEN):
#       adj_matrix[i][j] = min(adj_matrix[i][j], adj_matrix[i][k] + adj_matrix[k][j])
#     print('%f%% done...' % ((k*(int(MATRIX_LEN)**2) + i*int(MATRIX_LEN)) / ALL_OPERATIONS * 100))

# np.save('distance_matrix.npy', adj_matrix)

iterator = networkx.algorithms.all_pairs_dijkstra_path_length(graph)

distance = np.empty((args.width * args.height, args.width * args.height))
for source, target_dict in iterator:
  if source >= args.width * args.height: break
  for target in range(args.width * args.height):
    distance[source][target] = target_dict[target]
  print('%f%% done...' % (100 * source / (args.width * args.height)))

np.save('distance_matrix.npy', distance)
# np.savetxt('distance_matrix.csv', distance, delimiter=',', header='%dx%d\n' % (args.width, args.height))

print('All done!')