#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json

from dashboard.tests.test_panel_surveywizard import test_admin_edit_survey
from mobile.database import Database as MobileDatabase
from utils.fake_data import insert_fake_data
from dashboard.tests.fixtures import *

mobile_db = MobileDatabase()


def test_admin_get_survey_data(client):
    # create test survey with additional questions
    test_admin_edit_survey(client)
    login_credentials = {
        'email': 'test1_admin@email.com',
        'password': 'test123'
    }
    r = client.post('/v1/auth',
                    data=json.dumps(login_credentials),
                    content_type='application/json')
    jwt = json.loads(r.data)['accessToken']

    # retrieve empty result with no users in table
    params = {
        'searchString': '',
        'sorting': {},
        'pageIndex': 1,
        'itemsPerPage': 10
    }
    r = client.get('/v1/itinerum/users/table',
                   headers={'Authorization': 'JWT ' + jwt},
                   query_string=params)
    expected = {
        'status': 'success',
        'type': 'MobileUserTable',
        'results': {
            'pagination': {
                'totalPages': 0,
                'currentPage': 0,
                'totalItems': 0
            },
            'data': [],
            'columns': []
        }
    }
    assert json.loads(r.data) == expected

    # generate fake user data in database with mobile SQL functions
    insert_fake_data(database=mobile_db, survey_name='TestSurvey', users=25)

    r = client.get('/v1/itinerum/users/table',
                   headers={'Authorization': 'JWT ' + jwt},
                   query_string=params)
    assert len(json.loads(r.data)['results']['data']) == 10

    # ensure last page returns only leftover results
    params['pageIndex'] = 3
    r = client.get('/v1/itinerum/users/table',
                   headers={'Authorization': 'JWT ' + jwt},
                   query_string=params)
    assert len(json.loads(r.data)['results']['data']) == 5