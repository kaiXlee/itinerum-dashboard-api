#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json

from dashboard.tests.fixtures import *


# the most basic test of all: ensure the root url returns an empty success response
def test_empty_base_route_success(client):
    r = client.get('/v1/')
    expected = {
        'results': None,
        'status': 'success',
        'type': 'BaseIndex'
    }
    assert r.status_code == 200 and json.loads(r.data) == expected
