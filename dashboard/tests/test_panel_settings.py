#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json

from admin.database import Database as AdminDatabase
from dashboard.tests.common import get_jwt
from dashboard.tests.fixtures import *


admin_db = AdminDatabase()
TEST_AVATAR_PATH = './misc/test_avatar.jpg'


def test_settings_admin_set_survey_avatar_success(survey_client):
    credentials = {
        'email': 'test1_admin@email.com',
        'password': 'test123'
    }

    # get an admin jwt token
    jwt = get_jwt(survey_client, credentials)

    # get default and set custom avatar
    r = survey_client.get('/v1/profile/avatar',
                          headers={'Authorization': 'JWT ' + jwt},
                          content_type='multipart/form-data')
    expected = {
        'status': 'success',
        'type': 'SurveyProfileAvatar',
        'results': {
            'avatarUri': '/assets/static/defaultAvatar.png'
        }
    }
    assert json.loads(r.data) == expected

    with open(TEST_AVATAR_PATH, 'rb') as avatar_f:
        files = {'avatar': avatar_f}
        r = survey_client.post('/v1/profile/avatar',
                               headers={'Authorization': 'JWT ' + jwt},
                               data=files,
                               content_type='multipart/form-data')
        assert '/assets/user/avatars' in json.loads(r.data)['results']['avatarUri']


def test_settings_admin_set_prompts_parameters(survey_client):
    credentials = {
        'email': 'test1_admin@email.com',
        'password': 'test123'
    }

    # get an admin jwt token
    jwt = get_jwt(survey_client, credentials)

    # fetch the default survey settings and update prompts parameters
    r = survey_client.get('/v1/settings',
                          headers={'Authorization': 'JWT ' + jwt},
                          content_type='application/json')
    assert r.status_code == 200
    results = json.loads(r.data)['results']
    expected = {
        'tripbreakerSubwayStationBufferMeters': 300,
        'termsOfService': None,
        'aboutText': None,
        'surveyRecordMode': True,
        'surveyMaxDays': 14,
        'surveyRecordAcceleration': True,
        'contactEmail': 'test1_admin@email.com',
        'surveyId': 1,
        'surveyStart': None,
        'tripbreakerIntervalSeconds': 360,
        'surveyMaxPrompts': 20
    }
    assert results == expected

    new_settings = {
        'aboutText': 'sample about text',
        'termsOfService': 'sample terms of service',
        'contactEmail': 'test1_contact@email.com',
        'surveyMaxDays': 100,
        'surveyMaxPrompts': 50,
        'tripbreakerIntervalSeconds': 5,
        'tripbreakerSubwayStationBufferMeters': 20
    }
    r = survey_client.post('/v1/settings',
                           data=json.dumps(new_settings),
                           headers={'Authorization': 'JWT ' + jwt},
                           content_type='application/json')
    assert r.status_code == 201
    assert json.loads(r.data)['results'] == new_settings

