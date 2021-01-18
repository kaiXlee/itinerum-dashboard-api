#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask import jsonify, request, wrappers
from flask_restful import Resource

from utils.flask_jwt import jwt_refresh
from utils.responses import Success


class BaseIndexRoute(Resource):
    headers = {'Location': '/'}

    def get(self):
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type='BaseIndex',
                       body=None)


class BaseRefreshJWTRoute(Resource):
    headers = {'Location': '/auth/refresh'}

    def post(self):
        token = request.headers.get('Authentication')
        if token == 'null':
            return

        response = jwt_refresh(token)
        if isinstance(response, wrappers.Response):
            return response
        else:
            return jsonify(response)
