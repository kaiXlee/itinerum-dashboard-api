#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import csv
from datetime import datetime
import dateutil.parser
from flask import request
from flask_restful import Resource
from flask_security import roles_accepted

from dashboard.database import Database
from models import db
from utils.flask_jwt import jwt_required, current_identity
from utils.geo import to_points_geojson, to_prompts_geojson, to_trips_geojson
from utils.responses import Success, Error
from utils.tripbreaker import algorithm as tripbreaker

database = Database()


class MapperPointsRoute(Resource):
    headers = {'Location': '/itinerum/users/<string:uuid>/points'}
    resource_type = 'MapperPoints'

    @jwt_required()
    @roles_accepted('admin', 'researcher', 'participant')
    def get(self, uuid):
        survey = database.survey.get(current_identity.survey_id)

        start = request.values.get('startTime')
        end = request.values.get('endTime')

        collection_start, collection_end = database.mobile_user.active_period(survey, uuid)
        if not (start and end):
            start = datetime(year=collection_end.year,
                             month=collection_end.month,
                             day=collection_end.day,
                             hour=0,
                             minute=0,
                             second=0,
                             tzinfo=collection_end.tzinfo)
            end = datetime(year=collection_end.year,
                           month=collection_end.month,
                           day=collection_end.day,
                           hour=23,
                           minute=59,
                           second=59,
                           tzinfo=collection_end.tzinfo)
        else:
            start = dateutil.parser.parse(start)
            end = dateutil.parser.parse(end)


        gps_points = database.mobile_user.coordinates(survey=survey,
                                                      uuid=uuid,
                                                      start_time=start,
                                                      end_time=end)

        prompt_responses = database.mobile_user.prompt_responses(survey=survey,
                                                                 uuid=uuid,
                                                                 start_time=start,
                                                                 end_time=end)

        cancelled_prompts = database.mobile_user.cancelled_prompts(survey=survey,
                                                                   uuid=uuid,
                                                                   start_time=start,
                                                                   end_time=end)

        # returns bare response to be returned as msgpack
        return {
            'uuid': uuid,
            'points': to_points_geojson(gps_points),
            'promptResponses': to_prompts_geojson(prompt_responses, group_by='displayed_at'),
            'cancelledPrompts': to_prompts_geojson(cancelled_prompts),
            'collectionStart': collection_start.isoformat(),
            'collectionEnd': collection_end.isoformat(),
            'searchStart': start.isoformat(),
            'searchEnd': end.isoformat()
        }


class MapperTripsRoute(Resource):
    headers = {'Location': '/itinerum/users/<string:uuid>/trips'}
    resource_type = 'MapperTrips'

    @jwt_required()
    def get(self, uuid):
        survey = database.survey.get(current_identity.survey_id)
        start = dateutil.parser.parse(request.values.get('startTime'))
        end = dateutil.parser.parse(request.values.get('endTime'))

        parameters = {
            'break_interval_seconds': survey.trip_break_interval,
            'cold_start_distance_meters': survey.trip_break_cold_start_distance,
            'subway_buffer_meters': survey.trip_subway_buffer,
            'accuracy_cutoff_meters': survey.gps_accuracy_threshold
        }
        gps_points = database.mobile_user.coordinates(survey, uuid, start, end)
        trips, summaries = tripbreaker.run(parameters, survey.subway_stops, gps_points)

        response = {
            'trips': to_trips_geojson(trips, summaries) if trips else {},
            'searchStart': start.isoformat(),
            'searchEnd': end.isoformat()            
        }
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=response)


class MapperSubwayStationsRoute(Resource):
    headers = {'Location': '/itinerum/tripbreaker/subway'}
    resource_type = 'MapperSubwayStations'

    @jwt_required()
    @roles_accepted('admin', 'researcher')
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        response = {
            'stations': to_prompts_geojson(survey.subway_stops),
            'bufferSize': survey.trip_subway_buffer
        }
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=response)

    @jwt_required()
    @roles_accepted('admin', 'researcher')
    def post(self):
        survey = database.survey.get(current_identity.survey_id)
        data = request.files.get('stops')

        dialect = csv.Sniffer().sniff(data.read(), delimiters=';,')
        data.seek(0)
        reader = csv.DictReader(data, dialect=dialect)
        reader.fieldnames = [name.lower() for name in reader.fieldnames]

        # determine the keys out of the options for the lat/lng columns
        location_columns = None
        location_columns_options = [('latitude', 'longitude'),
                                    ('lat', 'lng'),
                                    ('y', 'x')]

        for columns in location_columns_options:
            if set(columns).issubset(set(reader.fieldnames)):
                location_columns = columns

        # insert subway stations into database
        if location_columns:
            rename = ('latitude' and 'longitude') not in location_columns
            if rename:
                reader = self._rename_columns(location_columns, reader)

            subway_stops = database.survey.upsert_subway_stops(survey=survey, stops=reader)
            return Success(status_code=201,
                           headers=self.headers,
                           resource_type=self.resource_type,
                           body={'stations': to_prompts_geojson(subway_stops)})
        return Error(status_code=400,
                     headers=self.headers,
                     resource_type=self.resource_type,
                     errors=['Failed to parse subway stops .csv file'])

    @jwt_required()
    @roles_accepted('admin', 'researcher')
    def delete(self):
        survey = database.survey.get(current_identity.survey_id)
        survey.subway_stops.delete()
        db.session.commit()
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body={'stations': {'features': []}})

    # change selected column keys to latitude and longitude
    def _rename_columns(self, location_columns, rows):
        lat_label, lng_label = location_columns
        for row in rows:
            row['latitude'] = row.pop(lat_label)
            row['longitude'] = row.pop(lng_label)
            yield row
