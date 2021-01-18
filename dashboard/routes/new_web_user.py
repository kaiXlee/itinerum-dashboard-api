#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask import request
from flask_restful import Resource
from flask_security import roles_required

from dashboard.database import Database
from utils.data import make_keys_camelcase
from utils.flask_jwt import jwt_required, current_identity
from utils.responses import Success, Error
from utils.validators import validate_json, value_exists

database = Database()


class NewWebUserSignupRoute(Resource):
    resource_type = 'NewWebUserSignup'
    headers = {'Location': '/auth/signup'}

    def post(self):
        validations = [{
            'email': {
                'key': 'email',
                'validator': value_exists,
                'response': Error,
                'error': 'Email cannot be blank.',
            },
            'password': {
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
            }
        }]
        validated = validate_json(validations, self.headers, self.resource_type)
        survey = database.survey.find_by_name(validated['survey_name'])

        # create a researcher user if a signup token is provided
        researcherToken = request.json.get('registrationToken', '').strip()
        if researcherToken:
            user = database.web_user.create_researcher(survey=survey,
                                                       email=validated['email'],
                                                       password=validated['password'],
                                                       token=researcherToken)

            if user is False:
                return Error(status_code=400,
                             headers=self.headers,
                             resource_type=self.resource_type,
                             errors=['Web user already exists for email.'])
            elif user is None:
                return Error(status_code=403,
                             headers=self.headers,
                             resource_type=self.resource_type,
                             errors=['Researcher user could not be created.'])

        else:
            mobile_user = database.mobile_user.find_by_email(email=validated['email'])
            if not mobile_user:
                return Error(status_code=404,
                             headers=self.headers,
                             resource_type=self.resource_type,
                             errors=['Participant email not found in any survey response.'])
            else:
                user = database.web_user.create_participant(survey,
                                                            email=validated['email'],
                                                            password=validated['password'],
                                                            uuid=mobile_user.uuid)
                if user is False:
                    return Error(status_code=400,
                                 headers=self.headers,
                                 resource_type=self.resource_type,
                                 errors=['Participant user could not be created.'])
        return Success(status_code=201,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=make_keys_camelcase(validated))


class NewWebUserResearcherTokenRoute(Resource):
    headers = {'Location': '/auth/signup/code'}
    resource_type = 'NewWebUserResearcherToken'

    @jwt_required()
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        token = database.web_user.get_invite_researcher_token(survey)
        if not token:
            token = database.web_user.create_invite_researcher_token(survey)
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body={'token': token.token})

    @jwt_required()
    @roles_required('admin')
    def post(self):
        survey = database.survey.get(current_identity.survey_id)
        response = {
            'token': database.web_user.create_invite_researcher_token(survey).token
        }
        return Success(status_code=201,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=response)
