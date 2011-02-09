#!/usr/bin/env python2.6
"""
Populate mongo collection with initial buoy data from csv source file.
Add geospatial index.
"""

import csv
from pymongo import Connection, GEO2D

INPUT_FILE = "data/all_buoys.csv"

buoy_csv = csv.reader(open(INPUT_FILE))
header = buoy_csv.next()

connection = Connection()
db = connection.surf_log
buoys = db.buoys

for row in buoy_csv:
    buoy = {'_id': row[0],
            'loc': (float(row[2]), float(row[1])),
            'description': row[3],
            'online': True}
    buoys.update({'buoy_id': '%s' % row[0]}, buoy, upsert=True)
    status = db.last_status()
    if not status.get("updatedExisting"):
        print "Inserted new buoy %s" % row[0]
    else:
        print "Updated buoy %s" % row[0]
        
buoys.create_index([("loc", GEO2D)])

