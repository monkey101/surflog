#!/usr/bin/env python2.6

from pymongo import Connection, GEO2D


connection = Connection()
db = connection.surf_log
buoys = db.buoys

center = [-74, 40.74]
RADIUS_OF_THE_EARTH = 3959
radians = 0.09

# Get the near results with distances
near_dict = db.command( "geoNear", "buoys", near = center, maxDistance = radians, spherical = True ); 
print len(near_dict.get("results"))
for result in near_dict.get("results"):
    print "%s at %s is %s" % (result.get("obj").get("buoy_id"), result.get("obj").get("loc"), result.get("dis"))

near_buoys = buoys.find({"loc" : {"$within" : {"$centerSphere" : [center, radians]}}}).limit(1)
    
near_buoys = buoys.find( { 'loc' : { '$nearSphere' : center, '$maxDistance' : radians} } ).limit(1)
print "\nCalculating near neighbors maxDistance of %s miles from %s" %  (radians * RADIUS_OF_THE_EARTH, center)
print near_buoys.count()
for buoy in near_buoys:
    print buoy

# Not sure why this one is returning 91 more results....
print "Calculating near neighbors within %s miles of %s" % (radians * RADIUS_OF_THE_EARTH, center)
print near_buoys.count()
for buoy in near_buoys:
    print buoy