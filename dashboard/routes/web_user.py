#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask import current_app, request
from flask_restful import Resource
from flask_security import roles_required
import json
import requests as requestslib

from dashboard.database import Database
from dashboard.routes.data_management import rq
from utils.data import extract_root_domain
from utils.flask_jwt import jwt_required, current_identity
from utils.responses import Success, Error

database = Database()


@rq.job
def email_password_token(mailgun_domain, mailgun_api_key, base_url, email, token):
    url = 'https://api.mailgun.net/v3/{}/messages'.format(mailgun_domain)
    return_url = '{base_url}/reset/password?email={email}&token={token}'.format(base_url=base_url,
                                                                                email=email,
                                                                                token=token)
    html_email = None
    with open('./dashboard/templates/reset_email-en.html', 'r') as reset_html_f:
        html_email = reset_html_f.read()
        html_email = html_email.format(link=return_url)

    root_domain = extract_root_domain(mailgun_domain)
    r = requestslib.post(url,
                         auth=('api', mailgun_api_key),
                         data={'from': 'Itinerum.ca <password@{}>'.format(root_domain),
                               'to': email,
                               'subject': 'Password reset request for Intinerum.ca',
                               'text': return_url,
                               'html': html_email})
    if r.status_code >= 300:
        raise Exception(r)


class WebUserPasswordResetRoute(Resource):
    headers = {'Location': '/auth/password/reset'}
    resource_type = 'WebUserPasswordReset'

    def post(self):
        email = request.json.get('email')
        base_url = request.json.get('baseUrl')

        token = database.web_user.create_reset_password_token(email)
        if token:
            email_password_token.queue(current_app.config['MAILGUN_DOMAIN'], 
                                       current_app.config['MAILGUN_API_KEY'],
                                       base_url, email, token.token)
            # email_password_token(current_app.config['MAILGUN_DOMAIN'], 
            #                      current_app.config['MAILGUN_API_KEY'],
            #                      base_url, email, token.token)

            return Success(status_code=201,
                           headers=self.headers,
                           resource_type=self.resource_type,
                           body={})
        return Error(status_code=401,
                     headers=self.headers,
                     resource_type=self.resource_type,
                     errors=['Email not found.'])

    def put(self):
        email = request.json.get('email')
        password = request.json.get('password')
        token = request.json.get('token')
        user = database.web_user.update_password(email, password, token)
        if user:
            return Success(status_code=201,
                           headers=self.headers,
                           resource_type=self.resource_type,
                           body={})
        return Error(status_code=401,
                     headers=self.headers,
                     resource_type=self.resource_type,
                     errors=[])


class WebUsersTableRoute(Resource):
    headers = {'Location': '/webusers/table'}
    resource_type = 'WebUsersTable'

    @jwt_required()
    @roles_required('admin')
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        sort_fields = json.loads(request.values.get('sorting', '{}'))
        page_index = int(request.values.get('pageIndex'))
        items_per_page = int(request.values.get('itemsPerPage'))

        response = database.web_user.paginated_table(survey=survey,
                                                     page_index=page_index,
                                                     items_per_page=items_per_page,
                                                     sort_fields=sort_fields)
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=response)


class WebUserDeleteRoute(Resource):
    headers = {'Location': '/webusers/<string:email>'}
    resource_type = 'WebUserDelete'

    @jwt_required()
    @roles_required('admin')
    def delete(self, email):
        survey = database.survey.get(current_identity.survey_id)
        user = survey.web_users.filter_by(email=email).one_or_none()
        if user:
            database.web_user.delete(user)
            return Success(status_code=201,
                           headers=self.headers,
                           resource_type=self.resource_type,
                           body={})
        return Error(status_code=401,
                     headers=self.headers,
                     resource_type=self.resource_type,
                     errors=['Web user could not be deleted from survey.'])
