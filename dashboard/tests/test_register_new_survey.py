#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json

from admin.database import Database as AdminDatabase
from dashboard.tests.fixtures import *

admin_db = AdminDatabase()
parameters = {
    'email': 'test1_admin@email.com',
    'password': 'test123',
    'surveyName': 'TestSurvey'
}


# fail validation with bad sign-up code
def test_registration_token_validation_failure(client):
    parameters['signupCode'] = 'abc'
    r = client.post('/v1/new/validate',
                    data=json.dumps(parameters),
                    content_type='application/json')
    expected = {
        'status': 'success',
        'type': 'NewSurveyValidation',
        'results': {
            'signupCode': False,
            'surveyName': True,
            'email': True
        }
    }
    assert json.loads(r.data) == expected


# get a valid sign-up token and successfully validate it
def test_registration_token_validation_success(client):
    token = admin_db.token.new_survey.get_active().token
    parameters.update({'signupCode': token})
    r = client.post('/v1/new/validate',
                    data=json.dumps(parameters),
                    content_type='application/json')
    expected = {
        'status': 'success',
        'type': 'NewSurveyValidation',
        'results': {
            'signupCode': True,
            'surveyName': True,
            'email': True
        }
    }
    assert json.loads(r.data) == expected


# create a new survey in the database and ensure that duplicate
# survey names and admin users cannot be used
def test_register_new_survey_success(client):
    # create the new survey with the valid signupCode
    token = admin_db.token.new_survey.get_active().token
    parameters.update({'signupCode': token})

    r = client.post('/v1/new',
                    data=json.dumps(parameters),
                    content_type='application/json')
    expected = {
        'status': 'success',
        'type': 'NewSurvey',
        'results': {
            'adminEmail': parameters['email'],
            'adminPassword': parameters['password'],
            'signupCode': parameters['signupCode'],
            'surveyName': parameters['surveyName']
        }
    }
    assert json.loads(r.data) == expected

    # ensure that trying to create a duplicate survey will fail validation
    r = client.post('/v1/new/validate',
                    data=json.dumps(parameters),
                    content_type='application/json')
    expected = {
        'status': 'success',
        'type': 'NewSurveyValidation',
        'results': {
            'signupCode': True,
            'surveyName': False,
            'email': False
        }
    }
    assert json.loads(r.data) == expected

    # ensure that a duplicate survey cannot be created
    r = client.post('/v1/new',
                    data=json.dumps(parameters),
                    content_type='application/json')
    expected = {
        'status': 'error',
        'type': 'NewSurvey',
        'errors': ['Survey already exists.']
    }
    assert json.loads(r.data) == expected

    # ensure that an administrator email cannot be used
    # for multiple surveys
    dupe_parameters = dict(parameters)
    dupe_parameters['surveyName'] = 'TestSurvey2'
    r = client.post('/v1/new',
                    data=json.dumps(dupe_parameters),
                    content_type='application/json')
    expected = {
        'status': 'error',
        'type': 'NewSurvey',
        'errors': ['Admin user could not be created.']
    }
    assert json.loads(r.data) == expected

    # test that admin user can login and receives appropriate user-level
    credentials = {
        'email': parameters['email'],
        'password': parameters['password'],
    }
    r = client.post('/v1/auth',
                    data=json.dumps(credentials),
                    content_type='application/json')
    response = json.loads(r.data)
    response.pop('accessToken')
    expected = {
        'surveyName': parameters['surveyName'],
        'userLevel': 0
    }
    assert response == expected
