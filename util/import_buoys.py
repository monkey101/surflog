#!/usr/bin/env python2.6
"""
Populate mongo collection with initial buoy data from csv source file.
Add geospatial index.
"""

import csv
import pymongo

INPUT_FILE = "data/all_buoys.csv"

buoy_csv = csv.reader(open(INPUT_FILE))
header = buoy_csv.next()

connection = pymongo.MongoClient("mongodb://dan:dan1275@surflog-shard-00-00-u9fko.mongodb.net:27017,surflog-shard-00-01-u9fko.mongodb.net:27017,surflog-shard-00-02-u9fko.mongodb.net:27017/foo?ssl=true&replicaSet=surflog-shard-0&authSource=admin")

db = connection.surf_log
buoys = db.buoys

for row in buoy_csv:
    buoy = {'_id': row[0],
            'loc': (float(row[2]), float(row[1])),
            'description': row[3],
            'online': True}
    buoys.update({'_id': '%s' % row[0]}, buoy, upsert=True)
    status = db.last_status()
    if not status.get("updatedExisting"):
        print "Inserted new buoy %s" % row[0]
    else:
        print "Updated buoy %s" % row[0]

buoys.create_index([("loc", pymongo.GEOSPHERE)])

