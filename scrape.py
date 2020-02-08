import requests
import html
from bs4 import BeautifulSoup, NavigableString
from requests_html import HTMLSession
import json
import requests_html
from datetime import datetime
from statistics import median

DT_FORMAT = '%H:%M'

base_url = 'http://schedules.sofiatraffic.bg/'
response = requests.get(base_url)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.text, features="html.parser")

links = []
for transport_type in soup.find('div', {'id': 'lines_quick_access'}).find_all('div'):
  for line in transport_type.find_all('li'):
    if 'N' not in line.a['href'] and line.a['href'] != 'autobus/123':
      links.append(base_url + line.a['href'])

links.append('http://schedules.sofiatraffic.bg/metro/1')
  
routes = []  
for link in links:
  session = HTMLSession()
  print(link)
  link_response = session.get(link)
  link_response.html.render(sleep=1)
  
  page = link_response.html
  
  
  # for stops_list in link_response.html.find('.schedule_direction_signs')[:2]:
  #   stops = [(stop.find('input', first=True).text, stop.find('a', first=True).text) for stop in stops_list.find('li')]
  #   print(stops_list)
  
  dirs = len(page.find('.schedule_view_direction_tabs', first=True).find('li'))
  
  for stops_list, times_list, schedule_table in zip(page.find('.schedule_direction_signs')[:dirs], page.find('.line_print_route')[:dirs], page.find('.schedule_times')[:dirs]):
    stops = [(stop_time.find('.stop_minutes_print', first=True).text, stop.find('a', first=True).text) for stop, stop_time in zip(stops_list.find('li'), times_list.find('li'))]
    schedule_times = [cell.text for cell in schedule_table.find('.hours_cell a')]
    schedule_diffs = [(datetime.strptime(t2, DT_FORMAT) - datetime.strptime(t1, DT_FORMAT)).seconds / 60 for t1, t2 in zip(schedule_times[:-1], schedule_times[1:])]
    if len(schedule_diffs) == 0: continue # No times on timetable.
    
    routes.append({'stops': stops, 'median_wait': median(schedule_diffs)})
  
  session.close()

with open('routes.txt', 'w') as file:
  json.dump(routes, file)
