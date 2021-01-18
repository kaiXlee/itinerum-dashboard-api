#!/usr/bin/env python
# Kyle Fitzsimmons, 2016
import math
import time
import utm

# python 2+3 cpickle import
try:
    import _pickle as cPickle
except ImportError:
    import cPickle


def process_utm(points):
    '''Convert WGS84 lat/lon points to UTM for performing spatial queries'''
    processed = []

    for p in points:
        easting, northing, _, _ = utm.from_latlon(p.latitude, p.longitude)
        processed.append({
            'id': p.id,
            'timestamp': p.timestamp,
            'latitude': p.latitude,
            'longitude': p.longitude,
            'easting': easting,
            'northing': northing,
            'h_accuracy': p.h_accuracy,
            'p_accuracy': p.v_accuracy
        })
    return processed


# hackish way to copy a dictionary faster than deepcopy
def quick_deepcopy(dictionary):
    return cPickle.loads(cPickle.dumps(dictionary, -1))


def pythagoras(point1, point2):
    '''Calculate the distance in meters between two UTM points'''
    a = point2[0] - point1[0]
    b = point2[1] - point1[1]
    d = math.sqrt(a**2 + b**2)
    return d


def velocity_check(point1, point2, period):
    '''Check if a missing period is above a minimum velocity threshold to indicate that
       an unusually large time gap is a movement period and a continuation of a trip'''
    minimum_walking_speed = 15.0 * 1000 / 3600
    if period:
        if (pythagoras(point1, point2) / period) > minimum_walking_speed:
            return True
        else:
            return False
    else:
        return False
