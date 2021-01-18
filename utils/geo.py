#!/usr/bin/env python
# Kyle Fitzsimmons, 2017
#
# Utils: geographic utility functions (TODO: make more generic)
from datetime import datetime
from decimal import Decimal
from utils.data import cast, make_keys_camelcase


### Return points as linestring
def to_points_geojson(query_result):
    '''Geojson generated for polyline data from detected trips'''
    geojson = {
        'crs': {
            'type': 'name',
            'properties': {
                'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'
            }
        },
        'type': 'FeatureCollection',
        'features': []
    }

    # create each trip line
    feature = {
        'type': 'Feature',
        'properties': {},
        'geometry': {
            'type': 'LineString',
            'coordinates': []
        }
    }

    for i, row in enumerate(query_result):
        if i == 0:
            feature['properties']['startTime'] = row.timestamp.isoformat()
        feature['geometry']['coordinates'].append((cast(row.latitude, float), cast(row.longitude, float)))
        feature['properties']['endTime'] = row.timestamp.isoformat()
        feature['properties']['numPoints'] = i + 1
    geojson['features'] = [feature]
    return geojson


def to_trips_geojson(trips_result, summaries_result):
    '''Geojson generated for polyline data from detected trips'''
    geojson = {
        'crs': {
            'type': 'name',
            'properties': {
                'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'
                }
            },
        'type': 'FeatureCollection',
        'features': []
    }

    for trip_id, trip in trips_result.items():
        if trip:
            # create each trip line
            feature = {
                'type': 'Feature',
                'properties': {
                    'start': trip[0]['timestamp'].isoformat(),
                    'end': trip[-1]['timestamp'].isoformat(),
                    'tripCode': trip[0]['trip_code'],
                    'cumulativeDistance': summaries_result[trip_id]['cumulative_distance']
                },
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [(cast(p['latitude'], float), cast(p['longitude'], float)) for p in trip]
                }
            }

            geojson['features'].append(feature)
    return geojson


def to_prompts_geojson(query_result, group_by=None):
    # group multiple prompt responses into a single feature
    sorted_prompts = []
    if group_by:
        grouped_prompts = {}
        grouped_responses = {}
        for row in query_result:
            timestamp = getattr(row, group_by).isoformat()
            grouped_prompts.setdefault(timestamp, []).append(row)
            response_str = row.response
            if isinstance(row.response, list):
                response_str = ', '.join(row.response)
            grouped_responses.setdefault(timestamp, []).append(response_str)

        for timestamp, prompts in sorted(grouped_prompts.items()):
            for prompt in prompts:
                prompt.responses = grouped_responses[timestamp]
                sorted_prompts.append(prompt)
    else:
        sorted_prompts = query_result

    # generate the geojson data
    geojson = {
        'type': 'FeatureCollection',
        'features': []
    }
    cols = None
    for row in sorted_prompts:
        if not cols:
            cols = row.__table__.columns.keys()
            cols.pop(cols.index('latitude'))
            cols.pop(cols.index('longitude'))

            if group_by:
                cols.pop(cols.index('response'))
                cols.append('responses')

        feature = {
            'type': 'Feature',
            'properties': {},
            'geometry': {
                'type': 'Point',
                'coordinates': [float(row.longitude), float(row.latitude)]
            }
        }

        for col in cols:
            value = getattr(row, col)
            if isinstance(value, datetime):
                value = value.isoformat()
            if isinstance(value, Decimal):
                value = float(value)
            feature['properties'][col] = value
        feature = make_keys_camelcase(feature)
        geojson['features'].append(feature)
    return geojson
