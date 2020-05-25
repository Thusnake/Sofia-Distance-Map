import numpy as np
import requests
import json
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument('token', type=str)
parser.add_argument('-w --width', dest='width', type=int, default=100)
parser.add_argument('-h --height', dest='height', type=int, default=100)

args = parser.parse_args() 

WESTMOST_LAT = 23.19
EASTMOST_LAT = 23.47
NORTHMOST_LON = 42.79
SOUTHMOST_LON = 42.60

COVER_LAT = abs(EASTMOST_LAT - WESTMOST_LAT)
COVER_LON = abs(NORTHMOST_LON - SOUTHMOST_LON)

GEO_FETCH_URL = 'https://eu1.locationiq.com/v1/reverse.php?key=%s&lat=%.6f&lon=%.6f&format=json&zoom=14'

HOR_PIXELS, VER_PIXELS = args.width, args.height

square_info = {x: None for x in range(HOR_PIXELS * VER_PIXELS)}

encoder = json.JSONEncoder()

def fetchSquare(x: int, y: int):
  square_center_x = x / HOR_PIXELS * COVER_LAT + WESTMOST_LAT + COVER_LAT / HOR_PIXELS / 2
  square_center_y = y / VER_PIXELS * COVER_LON + SOUTHMOST_LON + COVER_LON / VER_PIXELS / 2
  status = 0
  while status != 200:
    response = requests.get(GEO_FETCH_URL % (args.token, square_center_y, square_center_x))
    status = response.status_code
    
    if status != 200: 
      print('Error: Status %d' % status)
      print(response.headers)
      if retry_time := response.headers.get('Retry-After', None):
        print('Retrying in %d seconds...' % retry_time)
        time.sleep(float(retry_time))
      else:
        time.sleep(1)

  jres = response.json()
  
  global square_info
  square_info[x + y * HOR_PIXELS] = jres['address']
  
def fetchAll():
  start_time = time.time()
  
  for y in range(VER_PIXELS):
    for x in range(HOR_PIXELS):
      fetchSquare(x, y)
      print('Fetched %d, %d' % (x, y))
      
      avg_secs_per_square = (time.time() - start_time) / (x + 1 + y * HOR_PIXELS)
      est_remaining = (HOR_PIXELS - x + (VER_PIXELS - y - 1) * HOR_PIXELS) * avg_secs_per_square
      print('Est. remaining: %.2f minutes' % (est_remaining / 60))
      
      time.sleep(1)
    
    with open('square_info.json', 'w') as file:
      file.write(encoder.encode(square_info))
      print('Output up to y = %d saved to file.' % y)

if __name__ == '__main__':
  fetchAll()