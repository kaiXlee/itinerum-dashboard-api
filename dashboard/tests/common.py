#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json


def get_jwt(survey_client, parameters):
    login_credentials = {
        'email': parameters['email'],
        'password': parameters['password']
    }
    r = survey_client.post('/v1/auth',
                           data=json.dumps(login_credentials),
                           content_type='application/json')
    jwt = json.loads(r.data)['accessToken']
    return jwt
