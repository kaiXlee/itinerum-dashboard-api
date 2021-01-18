#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask import request
from flask_restful import Resource
from flask_security import roles_required

from dashboard.database import Database
from utils.data import make_keys_camelcase
from utils.flask_jwt import jwt_required, current_identity
from utils.responses import Success

database = Database()


class PromptsWizardEditRoute(Resource):
    headers = {'Location': '/promptswizard/edit'}
    resource_type = 'PromptsWizardEdit'

    @jwt_required()
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        prompts = database.prompts.formatted_prompt_questions(survey)
        response = {
            'survey_id': survey.id,
            'prompts': prompts,
            'started': True if database.survey.get_start_time(survey) else False
        }
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=make_keys_camelcase(response))

    @jwt_required()
    @roles_required('admin')
    def post(self):
        survey = database.survey.get(current_identity.survey_id)
        database.prompts.update(survey=survey,
                                prompts=request.json['prompts'])

        return Success(status_code=201,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=request.json)
