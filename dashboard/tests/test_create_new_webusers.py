#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json

# from admin.database import Database as AdminDatabase
from dashboard.database import Database as DashboardDatabase
from dashboard.tests.fixtures import *

# admin_db = AdminDatabase()
dashboard_db = DashboardDatabase()


def test_signup_researcher_webuser(client):
    # fail signing up researcher with bad token
    researcher_parameters = {
        'email': 'test1_researcher@email.com',
        'password': 'abc123',
        'surveyName': 'TestSurvey',
        'registrationToken': 'abc'
    }
    r = client.post('/v1/auth/signup',
                    data=json.dumps(researcher_parameters),
                    content_type='application/json')
    expected = {
        'status': 'error',
        'type': 'NewWebUserSignup',
        'errors': ['Researcher user could not be created.']
    }
    assert json.loads(r.data) == expected

    # create a survey and successfully sign-up researcher user
    new_survey_token = dashboard_db.survey.get_active_token().token
    survey_parameters = {
        'email': 'test1_admin@email.com',
        'password': 'test123',
        'surveyName': researcher_parameters['surveyName'],
        'signupCode': new_survey_token
    }
    r = client.post('/v1/new',
                    data=json.dumps(survey_parameters),
                    content_type='application/json')

    survey = dashboard_db.survey.find_by_name(researcher_parameters['surveyName'])
    new_researcher_token = dashboard_db.web_user.get_invite_researcher_token(survey).token
    researcher_parameters.update({'registrationToken': new_researcher_token})
    r = client.post('/v1/auth/signup',
                    data=json.dumps(researcher_parameters),
                    content_type='application/json')
    expected = {
        'status': 'success',
        'type': 'NewWebUserSignup',
        'results': {
            'password': 'abc123',
            'surveyName': 'TestSurvey',
            'email': 'test1_researcher@email.com'
        }
    }
    assert json.loads(r.data) == expected

    # fail creating duplicate researcher
    r = client.post('/v1/auth/signup',
                    data=json.dumps(researcher_parameters),
                    content_type='application/json')
    expected = {
        'status': 'error',
        'type': 'NewWebUserSignup',
        'errors': ['Researcher user could not be created.']
    }
    assert json.loads(r.data) == expected

    # fail signing up participant with bad survey name
    participant_parameters = {
        'email': 'test1_participant@email.com',
        'password': 'abc123',
        'surveyName': 'BadSurvey'
    }
    r = client.post('/v1/auth/signup',
                    data=json.dumps(participant_parameters),
                    content_type='application/json')
    expected = {
        'status': 'error',
        'errors': ['Participant email not found in any survey response.'],
        'type': 'NewWebUserSignup'
    }
    assert json.loads(r.data) == expected


def test_reset_webuser_password(client):
    # create a new survey and sign-up researcher user
    new_survey_token = admin_db.token.new_survey.get_active().token
    survey_parameters = {
        'email': 'test1_admin@email.com',
        'password': 'test123',
        'surveyName': 'TestSurvey',
        'signupCode': new_survey_token
    }
    r = client.post('/v1/new',
                    data=json.dumps(survey_parameters),
                    content_type='application/json')

    survey = dashboard_db.survey.find_by_name(survey_parameters['surveyName'])
    new_researcher_token = dashboard_db.web_user.get_invite_researcher_token(survey).token
    researcher_parameters = {
        'email': 'test1_researcher@email.com',
        'password': 'abc123',
        'surveyName': 'TestSurvey',
        'registrationToken': new_researcher_token
    }
    r = client.post('/v1/auth/signup',
                    data=json.dumps(researcher_parameters),
                    content_type='application/json')

    # issue password reset token link
    init_reset_parameters = {
        'baseUrl': '__FILLER__',
        'email': researcher_parameters['email']
    }
    r = client.post('/v1/auth/password/reset',
                    data=json.dumps(init_reset_parameters),
                    content_type='application/json')
    assert r.status_code == 201

    # retrieve reset token from database and use to change password
    user = dashboard_db.web_user.find_by_email(researcher_parameters['email'])
    token = dashboard_db.web_user.get_reset_password_token(user)
    new_password_parameters = {
        'email': researcher_parameters['email'],
        'password': 'def123',
        'token': token.token
    }
    print(new_password_parameters)
    r = client.put('/v1/auth/password/reset',
                   data=json.dumps(new_password_parameters),
                   content_type='application/json')
    assert r.status_code == 201

    # login successfully with new password
    credentials = {
        'email': new_password_parameters['email'],
        'password': new_password_parameters['password'],
    }
    r = client.post('/v1/auth',
                    data=json.dumps(credentials),
                    content_type='application/json')
    assert r.status_code == 200


def test_signup_participant_webuser(client):
    # successfully sign-up participant user
    ## ADD ME

    # fail creating duplicate participant
    ## ADD ME
    pass
