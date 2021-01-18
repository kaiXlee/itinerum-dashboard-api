#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
#
# Configuration file to pass to api/__init__.py for creating Flask app
# with different run levels
from datetime import datetime, timedelta
import pytz
import os


DEFAULT_DEV_DB = 'postgresql://127.0.0.1/itinerum_dev'
DEFAULT_TEST_DB = 'postgresql://127.0.0.1/itinerum_test'
DEFAULT_PRODUCTION_DB = 'postgresql://127.0.0.1/itinerum'


class Config(object):
    CONF = 'base'
    APP_HOST = '0.0.0.0'
    APP_PORT = int(os.environ.get('IT_DASHBOARD_PORT', 9000))
    APP_ROOT = '/dashboard/v1'
    ASSETS_ROUTE = '/assets'
    DEFAULT_AVATAR_FILENAME = 'defaultAvatar.png'
    MINIMUM_DATETIME = datetime(2017, 5, 1, tzinfo=pytz.utc)
    SECRET_KEY = os.environ.get('IT_SECRET_KEY', 'ChangeMe')
    SECURITY_PASSWORD_SALT = os.environ.get('IT_PASSWORD_SALT', 'ChangeMe')
    SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RQ_REDIS_URL = os.environ.get('REDIS_SERVER', 'redis://localhost:6379') + '/0'
    RQ_QUEUES = ['default']
    SSE_REDIS_URL = os.environ.get('REDIS_SERVER', 'redis://localhost:6379') + '/1'


# Dashboard API config ========================================================
class DashboardConfig(Config):
    APP_NAME = 'ItinerumDashboardAPI'
    ASSETS_FOLDER = '/assets'
    JWT_EXPIRATION_DELTA = timedelta(minutes=60)
    JWT_LEEWAY = timedelta(seconds=0)
    JWT_AUTH_URL_RULE = '/dashboard/v1/auth'
    JWT_AUTH_USERNAME_KEY = 'email'
    SIGNUP_EXPIRATION = (60 * 60 * 24) * 7  # one week
    # CSRF protection can be safely disabled as jwt is used to authenticate sessions
    # http://stackoverflow.com/questions/21357182/csrf-token-necessary-when-using-stateless-sessionless-authentication
    WTF_CSRF_ENABLED = False
    MAILGUN_DOMAIN = os.environ.get('MAILGUN_DOMAIN')
    MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY')


class DashboardDevelopmentConfig(DashboardConfig):
    CONF = 'development'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('IT_POSTGRES_URI', DEFAULT_DEV_DB)
    ASSETS_FOLDER = os.path.expanduser('../itinerum-dashboard/assets')


class DashboardTestingConfig(DashboardConfig):
    CONF = 'testing'
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('IT_POSTGRES_URI', DEFAULT_TEST_DB)
    ASSETS_FOLDER = '/assets'    


class DashboardProductionConfig(DashboardConfig):
    CONF = 'production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('IT_POSTGRES_URI', DEFAULT_PRODUCTION_DB)
    ASSETS_ROUTE = '/assets'
    SENTRY_KEY = os.environ.get('SENTRY_KEY')
    SENTRY_SECRET = os.environ.get('SENTRY_SECRET')
    SENTRY_APP_ID = os.environ.get('SENTRY_APP_ID')
