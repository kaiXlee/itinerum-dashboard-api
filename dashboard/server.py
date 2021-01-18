#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask import Flask, current_app, jsonify, make_response
from flask_cors import CORS
from flask_principal import Identity, RoleNeed, identity_changed
from flask_restful import Api
from flask_security import Security
from flask_security.utils import verify_password
from flask_sse import sse
import os
import logging
import msgpack
from raven.contrib.flask import Sentry

import config
from models import db, user_datastore
from dashboard import routes
from dashboard.routes.data_management import rq
from utils.flask_jwt import JWT
from utils.validators import InvalidJSONError, invalid_JSON_handler


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(config.DashboardConfig.APP_NAME)


def load_app_config(testing):
    config_env_var = os.environ.get('CONFIG')
    if config_env_var:
        config_env_var = config_env_var.strip().lower()
    if testing is True:
        logger.info(' * Loading TESTING server configuration...')
        return config.DashboardTestingConfig

    # fallback on env variable
    elif config_env_var == 'development':
        logger.info(' * Loading DEVELOPMENT server configuration...')
        logger.info(' * Connected to: {}'.format(config.DashboardDevelopmentConfig.SQLALCHEMY_DATABASE_URI))
        return config.DashboardDevelopmentConfig
    elif config_env_var == 'testing':
        logger.info(' * Loading TESTING server configuration...')
        return config.DashboardTestingConfig
    else:
        logger.info(' * Loading PRODUCTION server configuration...')
        return config.DashboardProductionConfig


def create_app(testing=False):
    app = Flask(config.DashboardConfig.APP_NAME)
    cfg = load_app_config(testing)
    app.config.from_object(cfg)

    # Connect Flask-SQLAlchemy =================================================
    db.init_app(app)

    # Connect Sentry.io error reporting ========================================
    if app.config['CONF'] == 'production':
        logger.info(' * Starting Sentry.io reporting for application...')
        Sentry(app, dsn='https://{key}:{secret}@sentry.io/{app_id}'.format(
            key=app.config['SENTRY_KEY'],
            secret=app.config['SENTRY_SECRET'],
            app_id=app.config['SENTRY_APP_ID']))
    else:
        logger.info(' * Sentry.io reporting disabled.')

    # Connect Flask-Security ===================================================
    Security(app, user_datastore)

    # Connect Flask-JWT w/ custom addons =======================================
    def authenticate(email, password):
        user = user_datastore.find_user(email=email)
        if user and email == user.email and verify_password(password, user.password):
            return user
        return None

    def identity_loader(payload):
        current_user = user_datastore.find_user(id=payload['identity'])
        setattr(current_user, 'survey_id', payload['survey_id'])

        identity = Identity(current_user.email)
        if hasattr(current_user, 'roles'):
            for role in current_user.roles:
                identity.provides.add(RoleNeed(role))
        identity_changed.send(current_app._get_current_object(),
                              identity=identity)
        return current_user

    JWT(app, authenticate, identity_loader)

    # Connect Flask-CORS for localhost debugging ===============================
    CORS(app, supports_credentials=True)

    # Register dahboard API routes =============================================
    api = Api(app, prefix=app.config['APP_ROOT'])
    api.add_resource(routes.BaseIndexRoute, '/')
    api.add_resource(routes.NewSurveyRoute, '/new')
    api.add_resource(routes.NewSurveyValidationRoute, '/new/validate')
    api.add_resource(routes.NewWebUserSignupRoute, '/auth/signup')
    api.add_resource(routes.NewWebUserResearcherTokenRoute, '/auth/signup/code')
    api.add_resource(routes.BaseRefreshJWTRoute, '/auth/refresh')
    api.add_resource(routes.WebUserPasswordResetRoute, '/auth/password/reset')
    # survey profile endpoints
    api.add_resource(routes.SurveyProfileAvatarRoute, '/profile/avatar')
    # permissions endpoints
    api.add_resource(routes.WebUsersTableRoute, '/webusers/table')
    api.add_resource(routes.WebUserDeleteRoute, '/webusers/<string:email>')
    # survey & prompts wizard endpoints
    api.add_resource(routes.SurveyWizardEditRoute, '/surveywizard/edit')
    api.add_resource(routes.PromptsWizardEditRoute, '/promptswizard/edit')
    # metrics endpoints
    api.add_resource(routes.MetricsSurveyOverviewRoute, '/itinerum/metrics')
    # participants & mapper endpoints
    api.add_resource(routes.MobileUserListRoute, '/itinerum/users/')
    api.add_resource(routes.MobileUserTableRoute, '/itinerum/users/table')
    api.add_resource(routes.MapperPointsRoute, '/itinerum/users/<string:uuid>/points')
    api.add_resource(routes.MapperTripsRoute, '/itinerum/users/<string:uuid>/trips')
    api.add_resource(routes.MapperSubwayStationsRoute, '/itinerum/tripbreaker/subway')
    # data management endpoints
    api.add_resource(routes.DataManagementExportRawDataEventsRoute, '/data/export/raw/events')
    api.add_resource(routes.DataManagementExportTripsDataEventsRoute, '/data/export/trips/events')
    api.add_resource(routes.DataManagementSurveyStatusRoute, '/data/status')
    # settings endpoints
    api.add_resource(routes.SettingsRoute, '/settings')
    api.add_resource(routes.SettingsSurveyResetRoute, '/settings/reset')

    # Attach custom error handlers ============================================
    app.errorhandler(InvalidJSONError)(invalid_JSON_handler)

    # Handle content-type/msgpack requests ====================================
    # Used for efficiently sending large geojson data
    @api.representation('application/msgpack')
    def output_msgpack(data, code, headers=None):
        resp = make_response(msgpack.packb(data), code)
        resp.headers.extend(headers or {})
        return resp

    # Execute first-run database queries to setup account roles ===============
    @app.before_first_request
    def first_run():
        user_datastore.find_or_create_role(name='admin')
        user_datastore.find_or_create_role(name='researcher')
        user_datastore.find_or_create_role(name='participant')

    # Connect redis-queue =====================================================
    rq.init_app(app)

    # Connect flask-sse =======================================================
    app.register_blueprint(sse, url_prefix='/dashboard/v1/stream')

    # Register health check route for load balancer ===========================
    @app.route('/health')
    def ecs_health_check():
        response = {'status': 0}
        return make_response(jsonify(response))

    return app
