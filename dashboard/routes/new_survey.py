#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask import request
from flask_restful import Resource

from dashboard.database import Database
from utils.data import make_keys_camelcase
from utils.responses import Success, Error
from utils.validators import validate_json, value_exists


database = Database()


class NewSurveyRoute(Resource):
    resource_type = 'NewSurvey'
    headers = {'Location': '/new'}

    def post(self):
        validations = [{
            'admin_email': {
                'key': 'email',
                'validator': value_exists,
                'response': Error,
                'error': 'Email cannot be blank.',
            },
            'admin_password': {
                'key': 'password',
                'validator': value_exists,
                'response': Error,
                'error': 'Password cannot be blank.',
            },
            'survey_name': {
                'key': 'surveyName',
                'validator': value_exists,
                'response': Error,
                'error': 'Survey name cannot be blank.',
            },
            'signup_code': {
                'key': 'signupCode',
                'validator': database.survey.register.use_token,
                'response': Error,
                'error': 'Survey sign-up token is invalid.',
            }
        }]

        validated = validate_json(validations, self.headers, self.resource_type)

        errors = []
        survey = database.survey.register.create(survey_name=validated['survey_name'])
        if survey:
            admin_role = database.web_user.create_admin(survey=survey,
                                                        email=validated['admin_email'],
                                                        password=validated['admin_password'])
            reseacher_token = database.web_user.create_invite_researcher_token(survey)
        else:
            errors.append('Survey already exists.')

        if not errors:
            if not admin_role:
                errors.append('Admin user could not be created.')
            if not reseacher_token:
                errors.append('Initial invite reseacher token could not be created.')

        if errors:
            return Error(status_code=400,
                         headers=self.headers,
                         resource_type=self.resource_type,
                         errors=errors)
        return Success(status_code=201,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=make_keys_camelcase(validated))


# provide validation for typed input fields
class NewSurveyValidationRoute(Resource):
    resource_type = 'NewSurveyValidation'
    headers = {'Location': '/new/validate'}

    def post(self):
        results = {}
        # check if a survey with the same name exists
        survey_name = request.json.get('surveyName')
        if survey_name:
            if not database.survey.find_by_name(survey_name):
                results['survey_name'] = True
            else:
                results['survey_name'] = False

        # check if the email already exists in database
        email = request.json.get('email')
        if email:
            if not database.web_user.find_by_email(email):
                results['email'] = True
            else:
                results['email'] = False

        # check that entered signup code is valid
        signup_token = request.json.get('signupCode')
        if signup_token:
            if database.survey.register.validate_token(signup_token):
                results['signup_code'] = True
            else:
                results['signup_code'] = False

        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=make_keys_camelcase(results))
