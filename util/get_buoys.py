#!/usr/bin/python2.6
"""
Create a CSV of all the known NOAA buoys and their geolocation
"""

import csv
import urllib2
import re
import os
from BeautifulSoup import BeautifulSoup


NOAA_ROOT = "http://www.ndbc.noaa.gov"
OUTPUT_FILE = "data/all_buoys.csv"

buoy_csv = csv.writer(open(OUTPUT_FILE, "wb")) 
buoy_csv.writerow(['buoy_id', 'latitude', 'longitude', 'description'])

# parse the all buoys page into individual links to each buoy
all_buoys_url = os.path.join(NOAA_ROOT, "to_station.shtml")
print "Parsing all buoys page: %s" % all_buoys_url
try:
    all_buoys_page = urllib2.urlopen(all_buoys_url, timeout=5)
except:
    print "ERROR: Timed out opening all buoys page %s" % all_buoys_url

if not all_buoys_page:
    print "ERROR: Error opening all buoys page %s" % all_buoys_url
    exit(1)

all_soup = BeautifulSoup(all_buoys_page)
tags = all_soup.findAll(attrs={"href" : re.compile("station_page.php\?station=.*")})
if not tags:
    print "ERROR: Error parsing all buoys page %s" % all_buoys_url
    exit(1)

# compile some regex's that we'll need to parse each page
buoy_re = re.compile('.*href="(.*?)">(.*)<.*')
lat_re = re.compile('.*var currentstnlat = (.*?);.*')
lon_re = re.compile('.*var currentstnlng = (.*?);.*')
desc_re = re.compile('.*var currentstnname = (.*?);.*')

# parse out the individual buoy id and page location then get the buoy info
for buoy in tags:
    m = buoy_re.match(str(buoy))
    if not m:
        print "ERROR: regex failed for this buoy page: %s" % buoy
        continue
    buoy_page_url = os.path.join(NOAA_ROOT, m.group(1))
    buoy_id = m.group(2)

    # using each buoy id, get the location, name, etc.
    print 'Parsing: %s' % buoy_page_url
    try:
        buoy_soup = BeautifulSoup(urllib2.urlopen(buoy_page_url, timeout=5))
    except:
        print "ERROR: Timed out opening this buoy: %s" % buoy_page_url

    if not buoy_soup:
        print "ERROR: Couldn't load this buoy"
        continue
    script = buoy_soup.findAll(text=re.compile('.*stnlat.*'))
    m = lat_re.match(str(script))
    if not m:
        print "ERROR: No latitude geo data for this buoy"
        continue
    latitude = m.group(1)
    m = lon_re.match(str(script))
    if not m:
        print "ERROR: No longitude geo data for this buoy"
        continue
    longitude = m.group(1)

    m = desc_re.match(str(script))
    description = ''
    if m:
        description = m.group(1)
    else:
        print "WARNING: No description data for this buoy"

    buoy_csv.writerow([buoy_id, latitude, longitude, description])

print "All buoy locations parsed"
