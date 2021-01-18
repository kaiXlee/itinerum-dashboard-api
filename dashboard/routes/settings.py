#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask_restful import Resource
from flask_security import roles_accepted, roles_required

from dashboard.database import Database
from models import db
from utils.data import make_keys_camelcase
from utils.flask_jwt import jwt_required, current_identity
from utils.responses import Success, Error
from utils.validators import validate_json, value_exists

database = Database()


class SettingsRoute(Resource):
    headers = {'Location': '/settings'}
    resource_type = 'Settings'

    @jwt_required()
    @roles_accepted('researcher', 'admin')
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        start_time = database.survey.get_start_time(survey)
        if start_time:
            start_time = start_time.isoformat()

        contact_email = survey.contact_email
        if not contact_email:
            admin_user = database.survey.get_admin(survey)
            contact_email = admin_user.email

        response = {
            'survey_id': survey.id,
            'about_text': survey.about_text,
            'terms_of_service': survey.terms_of_service,
            'contact_email': contact_email,
            'survey_start': start_time,
            'survey_max_days': survey.max_survey_days,
            'survey_max_prompts': survey.max_prompts,
            'survey_record_acceleration': survey.record_acceleration,
            'survey_record_mode': survey.record_mode,
            'gps_accuracy_threshold_meters': survey.gps_accuracy_threshold,
            'tripbreaker_interval_seconds': survey.trip_break_interval,
            'tripbreaker_cold_start_distance_meters': survey.trip_break_cold_start_distance,
            'tripbreaker_subway_buffer_meters': survey.trip_subway_buffer
        }
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=make_keys_camelcase(response))

    @jwt_required()
    @roles_required('admin')
    def post(self):
        validations = [{
            'about_text': {
                'key': 'aboutText',
                'validator': None,
            },
            'terms_of_service': {
                'key': 'termsOfService',
                'validator': None
            },
            'contact_email': {
                'key': 'contactEmail',
                'validator': value_exists,
                'response': Error,
                'error': 'A contact email address must be specified.'
            },
            'survey_max_days': {
                'key': 'surveyMaxDays',
                'validator': value_exists,
                'response': Error,
                'error': 'A maximum number of survey prompt days must be entered.',
            },
            'survey_max_prompts': {
                'key': 'surveyMaxPrompts',
                'validator': value_exists,
                'response': Error,
                'error': 'A maximum number of survey prompts must be entered.',
            },
            'gps_accuracy_meters': {
                'key': 'gpsAccuracyThresholdMeters',
                'validator': value_exists,
                'response': Error,
                'error': 'A minimum GPS accuracy threshold must be specified. (Higher threshold is lower accuracy)'
            },
            'tripbreaker_interval_seconds': {
                'key': 'tripbreakerIntervalSeconds',
                'validator': value_exists,
                'response': Error,
                'error': 'Trip breaking interval must be provided.'
            },
            'tripbreaker_cold_start_meters': {
                'key': 'tripbreakerColdStartDistanceMeters',
                'validator': value_exists,
                'response': Error,
                'error': 'Trip breaking cold start distance must be provided.'
            },
            'tripbreaker_subway_buffer_meters': {
                'key': 'tripbreakerSubwayBufferMeters',
                'validator': value_exists,
                'response': Error,
                'error': 'Trip breaking subway buffer must be provided.'
            }
        }]
        validated = validate_json(validations, self.headers, self.resource_type)
        survey = database.survey.get(current_identity.survey_id)
        survey.about_text = validated['about_text']
        survey.terms_of_service = validated['terms_of_service']
        survey.contact_email = validated['contact_email']
        survey.max_survey_days = validated['survey_max_days']
        survey.max_prompts = validated['survey_max_prompts']
        survey.gps_accuracy_threshold = validated['gps_accuracy_meters']
        survey.trip_break_interval = validated['tripbreaker_interval_seconds']
        survey.trip_break_cold_start_distance = validated['tripbreaker_cold_start_meters']
        survey.trip_subway_buffer = validated['tripbreaker_subway_buffer_meters']
        db.session.commit()

        return Success(status_code=201,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=make_keys_camelcase(validated))


class SettingsSurveyResetRoute(Resource):
    headers = {'Location': '/settings/reset'}
    resource_type = 'SettingsSurveyReset'

    @jwt_required()
    @roles_required('admin')
    def post(self):
        survey = database.survey.get(current_identity.survey_id)
        database.survey.reset(survey)
        survey = database.survey.get_survey_questions_json(survey)
        return Success(status_code=201,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body={'survey': survey})
