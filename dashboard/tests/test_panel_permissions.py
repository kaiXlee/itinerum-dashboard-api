#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json

from dashboard.database import Database
from dashboard.tests.common import get_jwt
from dashboard.tests.fixtures import *
from utils.tokens import validate_registration_token

dashboard_db = Database()


def test_admin_get_researcher_signup_token_success(app, survey_client):
    # get an admin jwt token
    credentials = {
        'email': 'test1_admin@email.com',
        'password': 'test123'
    }
    jwt = get_jwt(survey_client, credentials)

    # refresh jwt
    r = survey_client.post('/v1/auth/refresh',
                           headers={'Authentication': jwt},  # note this uses Authentication vs Authorization
                                                             # and does not include the JWT header
                           content_type='application/json')
    response = json.loads(r.data)
    assert 'accessToken' in response and 'userLevel' in response
    jwt = response['accessToken']

    # retrieve and refresh researcher signup token
    r = survey_client.get('/v1/auth/signup/code',
                          headers={'Authorization': 'JWT ' + jwt},
                          content_type='application/json')
    token = json.loads(r.data)['results']['token']
    salt = app.config['SECURITY_PASSWORD_SALT']
    assert validate_registration_token(token, salt, expiration=5) is True
    assert validate_registration_token(token, salt, expiration=0) is False


def create_researcher(survey_client, parameters):
    survey = dashboard_db.survey.find_by_name(parameters['surveyName'])
    new_researcher_token = dashboard_db.web_user.get_invite_researcher_token(survey).token
    parameters.update({'registrationToken': new_researcher_token})
    parameters['email'] = 'test1_researcher@email.com'
    r = survey_client.post('/v1/auth/signup',
                           data=json.dumps(parameters),
                           headers={'Authorization': 'JWT ' + parameters['jwt']},
                           content_type='application/json')
    assert r.status_code == 201


def test_admin_get_web_users(survey_client):
    credentials = {
        'email': 'test1_admin@email.com',
        'password': 'test123'
    }
    parameters = {
        'email': 'test1_researcher@email.com',
        'password': 'test123',
        'surveyName': 'TestSurvey',
        'jwt': get_jwt(survey_client, credentials)
    }
    create_researcher(survey_client, parameters)

    query = {
        'sorting': json.dumps({'column': 'created_at', 'direction': 1}),
        'pageIndex': 1,
        'itemsPerPage': 10
    }
    r = survey_client.get('/v1/webusers/table',
                          query_string=query,
                          headers={'Authorization': 'JWT ' + parameters['jwt']},
                          content_type='application/json')
    assert r.status_code == 200
    results = json.loads(r.data)['results']
    assert results['pagination'] == {
        'totalPages': 1,
        'currentPage': 1,
        'totalItems': 2
    }
    assert len(results['data']) == 2


def test_admin_delete_researcher_user(survey_client):
    credentials = {
        'email': 'test1_admin@email.com',
        'password': 'test123'
    }
    parameters = {
        'email': 'test1_researcher@email.com',
        'password': 'test123',
        'surveyName': 'TestSurvey',
        'jwt': get_jwt(survey_client, credentials)
    }
    create_researcher(survey_client, parameters)
    user = dashboard_db.web_user.find_by_email(parameters['email'])
    assert user

    # delete the created researcher user
    r = survey_client.delete('/v1/webusers/{}'.format(parameters['email']),
                             headers={'Authorization': 'JWT ' + parameters['jwt']},
                             content_type='application/json')
    assert r.status_code == 201

    user = dashboard_db.web_user.find_by_email(parameters['email'])
    assert user is None
