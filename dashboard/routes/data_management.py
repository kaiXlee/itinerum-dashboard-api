#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import ciso8601
from flask import request
from flask_restful import Resource
from flask_rq2 import RQ
from flask_security import roles_accepted
from flask_sse import sse
import os

from dashboard.database import Database
from utils.data import make_keys_camelcase
from utils.filehandler import save_zip
from utils.flask_jwt import jwt_required, current_identity
from utils.responses import Success

database = Database()
rq = RQ()


@rq.exception_handler
def catch_rq_exceptions(job, *exc_info):
    raise Exception(job, exc_info)

class DataManagementSurveyStatusRoute(Resource):
    headers = {'Location': '/data/status'}
    resource_type = 'DataManagementSurveyStatus'

    @jwt_required()
    @roles_accepted('admin', 'researcher')
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        start = database.survey.get_start_time(survey)

        response = {
            'message': 'Survey has not begun.',
            'start_time': None,
            'last_export': None
        }

        if start:
            response['message'] = 'Survey has started'
            response['start_time'] = start.isoformat()
            response['last_export'] = survey.last_export

        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=make_keys_camelcase(response))


@rq.job
def mobile_data_dump(survey_id, start, end, timezone, sse_channel):
    survey = database.survey.get(survey_id)
    event_start_response = {
        'start': start.isoformat(),
        'end': end.isoformat(),
        'type': 'raw-export-started'
    }
    sse.publish(event_start_response, channel=sse_channel)
    basepath = os.path.join('user', 'exports')
    database.export._begin('raw', survey, basepath, start, end)
    basename = survey.pretty_name + '-responses'
    data = database.export.survey_data(survey, start, end, timezone)
    zip_filename = save_zip(basepath=basepath, basename=basename, data=data)
    export = database.export._finish('raw', survey, basepath, zip_filename)
    event_finished_response = make_keys_camelcase(export)
    event_finished_response['type'] = 'raw-export-complete'
    sse.publish(event_finished_response, channel=sse_channel)


class DataManagementExportRawDataEventsRoute(Resource):
    headers = {'Location': '/data/download/raw/events'}
    resource_type = 'DataManagementExportRawDataEvents'

    @jwt_required()
    @roles_accepted('admin', 'researcher')
    def get(self):
        survey_id = current_identity.survey_id
        start = ciso8601.parse_datetime(request.values.get('start'))
        end = ciso8601.parse_datetime(request.values.get('end'))
        timezone = request.values.get('timezone')
        sse_channel = request.values.get('channel')
        # sse.publish({'msg': 'starting exports...', 'type': 'request-ack'},
        #             channel=sse_channel)

        mobile_data_dump.queue(survey_id, start, end, timezone, sse_channel)
        # mobile_data_dump(survey_id, start, end, timezone, sse_channel)

        response = {
            'start': start.isoformat(),
            'end': end.isoformat()
        }
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=response)


@rq.job
def mobile_trips_dump(survey_id, start, end, timezone, sse_channel):
    survey = database.survey.get(survey_id)
    event_start_response = {
        'start': start.isoformat(),
        'end': end.isoformat(),
        'type': 'trips-export-started'
    }
    sse.publish(event_start_response, channel=sse_channel)
    basepath = os.path.join('user', 'exports')
    database.export._begin('trips', survey, basepath, start, end)
    data = database.export.trips_data(survey, start, end, timezone)
    basename = survey.pretty_name + '-' + 'trips'
    zip_filename = save_zip(basepath=basepath, basename=basename, data=data)
    export = database.export._finish('trips', survey, basepath, zip_filename)
    event_finish_response = make_keys_camelcase(export)
    event_finish_response['type'] = 'trips-export-complete'
    sse.publish(event_finish_response, channel=sse_channel)


class DataManagementExportTripsDataEventsRoute(Resource):
    headers = {'Location': '/data/download/trips/events'}
    resource_type = 'DataManagementExportTripsData'

    @jwt_required()
    @roles_accepted('admin', 'researcher')
    def get(self):
        survey_id = current_identity.survey_id
        start = ciso8601.parse_datetime(request.values.get('start'))
        end = ciso8601.parse_datetime(request.values.get('end'))
        timezone = request.values.get('timezone')
        sse_channel = request.values.get('channel')
        # sse.publish({'msg': 'starting exports...', 'type': 'request-ack'},
        #             channel=sse_channel)

        mobile_trips_dump.queue(survey_id, start, end, timezone, sse_channel)
        # mobile_trips_dump(survey_id, start, end, timezone, sse_channel)

        response = {
            'start': start.isoformat(),
            'end': end.isoformat()
        }
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=response)
