#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask import current_app, request
from flask_restful import Resource
from flask_security import roles_required

from dashboard.database import Database
from utils import filehandler
from utils.data import make_keys_camelcase
from utils.flask_jwt import jwt_required, current_identity
from utils.responses import Success, Error
from utils.validators import validate_json, value_exists

database = Database()


class SurveyProfileAvatarRoute(Resource):
    headers = {'Location': '/profile/avatar'}
    resource_type = 'SurveyProfileAvatar'

    @jwt_required()
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        uri = survey.avatar_uri

        # use default avatar if a custom one is not set
        if not uri:
            with current_app.app_context():
                uri = '{base}/static/{avatar}'.format(base=current_app.config['ASSETS_ROUTE'],
                                                      avatar=current_app.config['DEFAULT_AVATAR_FILENAME'])
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body={'avatarUri': uri})

    @jwt_required()
    @roles_required('admin')
    def post(self):
        survey = database.survey.get(current_identity.survey_id)
        img = request.files.get('avatar')

        # delete the previous avatar image file
        if survey.avatar_uri:
            filehandler.delete(survey.avatar_uri)

        # shrink avatar image size
        try:
            thumbnail = filehandler.make_thumbnail(img)
        except IOError as e:
            return Error(status_code=400,
                         headers=self.headers,
                         resource_type=self.resource_type,
                         errors=[e.message])

        filename = filehandler.save(thumbnail,
                                    extensions=set(['.jpg', '.jpeg', '.gif', '.png', '.bmp']))
        # get image uri by finding static folder within avatar path. This
        # is to dynamically include subfolders within the static assets folder
        with current_app.app_context():
            uri = '{base}/user/avatars/{file}'.format(base=current_app.config['ASSETS_ROUTE'],
                                                      file=filename)
            survey.avatar_uri = uri
            database.survey.update(survey)

        return Success(status_code=201,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body={'avatarUri': uri})

    @jwt_required()
    @roles_required('admin')
    def delete(self):
        survey = database.survey.get(current_identity.survey_id)
        if survey.avatar_uri:
            filehandler.delete(survey.avatar_uri)

        # reset to default avatar
        with current_app.app_context():
            default_avatar_uri = '{base}/user/{avatar}'.format(base=current_app.config['ASSETS_ROUTE'],
                                                               avatar=current_app.config['DEFAULT_AVATAR_FILENAME'])
            survey.avatar_uri = default_avatar_uri
            database.survey.update(survey)

        return Success(status_code=202,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body={'avatarUri': default_avatar_uri})


class SurveyWizardEditRoute(Resource):
    headers = {'Location': '/surveywizard/edit'}
    resource_type = 'SurveyWizardEdit'

    @jwt_required()
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        response = {
            'language': survey.language,
            'about_text': survey.about_text,
            'terms_of_service': survey.terms_of_service,
            'max_days': survey.max_survey_days,
            'max_prompts': survey.max_prompts,
            'survey': database.survey.get_survey_questions_json(survey),
            'survey_id': survey.id,
            'started': True if database.survey.get_start_time(survey) else False
        }
        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=make_keys_camelcase(response))

    @jwt_required()
    @roles_required('admin')
    def post(self):
        validations = [{
            'language': {
                'key': 'language',
                'validator': value_exists,
                'response': Error,
                'error': 'Language selection cannot be blank.',
            },
            'about_text': {
                'key': 'aboutText',
                'validator': value_exists,
                'response': Error,
                'error': 'Survey about text cannot be blank.',
            },
            'terms_of_service': {
                'key': 'termsOfService',
                'validator': value_exists,
                'response': Error,
                'error': 'Survey terms of service name cannot be blank.',
            }
        }]
        validated = validate_json(validations, self.headers, self.resource_type)
        survey = database.survey.get(current_identity.survey_id)
        database.survey.update(survey,
                               settings=validated,
                               questions=request.json['questions'])

        return Success(status_code=201,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=request.json)
