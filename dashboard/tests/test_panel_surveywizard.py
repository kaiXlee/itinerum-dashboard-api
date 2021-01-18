#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json

from admin.database import Database as AdminDatabase
from dashboard.tests.fixtures import *

admin_db = AdminDatabase()


def test_admin_edit_survey(client):
    # create test survey
    parameters = {
        'email': 'test1_admin@email.com',
        'password': 'test123',
        'surveyName': 'TestSurvey',
        'signupCode': admin_db.token.new_survey.get_active().token
    }
    r = client.post('/v1/new',
                    data=json.dumps(parameters),
                    content_type='application/json')
    # login with email and password to retrieve jwt
    login_credentials = {'email': parameters['email'], 'password': parameters['password']}
    r = client.post('/v1/auth',
                    data=json.dumps(login_credentials),
                    content_type='application/json')
    jwt = json.loads(r.data)['accessToken']

    # get base survey with hardcoded questions
    r = client.get('/v1/surveywizard/edit',
                   headers={'Authorization': 'JWT ' + jwt},
                   content_type='application/json')
    response = json.loads(r.data)
    assert response['status'] == 'success'
    assert response['results']['language'] == 'en'
    assert len(response['results']['survey']) == 11

    # update and retrieve survey with custom questions
    updated_questions = response['results']['survey']
    updated_questions.extend([{
        'id': 1,
        'prompt': 'Please select your favorite mode of travel',
        'fields': {'choices': ['car', 'bus', 'plane']},
        'colName': 'favoriteMode'
    }, {
        'id': 2,
        'prompt': 'Please choose from the following colors',
        'fields': {'choices': ['red', 'blue', 'green']},
        'colName': 'color'
    }, {
        'id': 3,
        'prompt': 'Enter any numberof your choice',
        'fields': {'number': ''},
        'colName': 'randomNum'
    }, {
        'id': 4,
        'prompt': 'Please pin your location on the map',
        'fields': {'latitude': 'null', 'longitude': 'null'},
        'colName': 'usersLocation'
    }, {
        'id': 5,
        'prompt': 'Write some text about this survey',
        'fields': {'text': 'Enter text here'},
        'colName': 'aTextField'
    }])

    data = {
        'language': 'en',
        'aboutText': 'Lorem ipsum',
        'termsOfService': 'Do you agree to participate in this survey?',
        'questions': updated_questions
    }
    r = client.post('/v1/surveywizard/edit',
                    headers={'Authorization': 'JWT ' + jwt},
                    data=json.dumps(data),
                    content_type='application/json')
    assert json.loads(r.data)['results'] == data


def test_admin_create_prompts(client):
    # create test survey
    parameters = {
        'email': 'test1_admin@email.com',
        'password': 'test123',
        'surveyName': 'TestSurvey',
        'signupCode': admin_db.token.new_survey.get_active().token
    }
    r = client.post('/v1/new',
                    data=json.dumps(parameters),
                    content_type='application/json')
    # login with email and password to retrieve jwt
    login_credentials = {'email': parameters['email'], 'password': parameters['password']}
    r = client.post('/v1/auth',
                    data=json.dumps(login_credentials),
                    content_type='application/json')
    jwt = json.loads(r.data)['accessToken']

    # update and retrieve survey with custom prompts
    r = client.get('/v1/promptswizard/edit',
                   headers={'Authorization': 'JWT ' + jwt},
                   content_type='application/json')
    response = json.loads(r.data)
    expected = {
        'status': 'success',
        'type': 'PromptsWizardEdit',
        'results': {
            'started': False,
            'surveyId': 1,
            'prompts': []
        }
    }
    assert response == expected

    updated_prompts = response['results']['prompts']
    updated_prompts.extend([{
        'id': 1,
        'prompt': 'Which mode are you currently traveling by?',
        'fields': {'choices': ['Car', 'Bus', 'Plane', 'Subway', 'Bike', 'Walk']},
        'colName': 'currentMode'
    }, {
        'id': 1,
        'prompt': 'Are you at work, home, or other?',
        'fields': {'choices': ['Home', 'Work', 'Other']},
        'colName': 'currentLocation'
    }, {
        'id': 2,
        'prompt': 'Please choose some modes:',
        'fields': {'choices': ['Plane', 'Bus', 'EmDrive Rocket', 'Chariot']},
        'colName': 'checkedModes'
    }])

    data = {'prompts': updated_prompts}
    r = client.post('/v1/promptswizard/edit',
                    headers={'Authorization': 'JWT ' + jwt},
                    data=json.dumps(data),
                    content_type='application/json')
    assert json.loads(r.data)['results'] == data
