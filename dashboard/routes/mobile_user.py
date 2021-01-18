#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask import request
from flask_restful import Resource
from flask_security import roles_accepted
import json

from dashboard.database import Database
from models import db, MobileUser, MobileCoordinate
from utils.flask_jwt import jwt_required, current_identity
from utils.responses import Success

database = Database()


class MobileUserListRoute(Resource):
    headers = {'Location': '/itinerum/users/'}
    resource_type = 'MobileUserList'

    @jwt_required()
    def get(self):
        if current_identity.has_role('admin') or current_identity.has_role('researcher'):
            survey = database.survey.get(current_identity.survey_id)
            survey_users = []

            users_with_coordinates = (survey.mobile_users.filter(
                db.exists().where(MobileUser.id == MobileCoordinate.mobile_id)))

            for user in users_with_coordinates:
                survey_users.append({
                    'uuid': user.uuid,
                    'created_at': user.created_at.isoformat()
                })
        else:
            survey_users = [{
                'uuid': current_identity.participant_uuid,
                'created_at': current_identity.created_at.isoformat()
            }]
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=survey_users)            


class MobileUserTableRoute(Resource):
    headers = {'Location': '/itinerum/users/table'}
    resource_type = 'MobileUserTable'

    @jwt_required()
    @roles_accepted('admin', 'researcher')
    def get(self):
        survey = database.survey.get(current_identity.survey_id)

        search_string = request.values.get('searchString', '').strip().lower()
        sort_fields = json.loads(request.values.get('sorting', '{}'))
        page_index = int(request.values.get('pageIndex'))
        items_per_page = int(request.values.get('itemsPerPage'))

        response = database.mobile_user.paginated_table(survey=survey,
                                                        page_index=page_index,
                                                        items_per_page=items_per_page,
                                                        search=search_string,
                                                        sort_fields=sort_fields)
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=response)
