#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import json
import os
import pytest

from admin.database import Database as AdminDatabase
import config
from dashboard.server import create_app
from models import db as _db

admin_db = AdminDatabase()


## Testing setup & teardown fixtures ==========================================
# create the testing flask application
@pytest.fixture(scope='session')
def app(request):
    app = create_app(testing=True)
    if os.environ.get('CONFIG') == 'debug':
        app.config['ASSETS_FOLDER'] = config.DashboardDevelopmentConfig.ASSETS_FOLDER

    # initialize an application context before running tests
    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()


# setup and remove the testing database
@pytest.fixture(scope='function')
def db(app, request):
    _db.app = app
    with app.app_context():
        _db.create_all()

        # create a test survey registration token
        admin_db.token.new_survey.create()

    yield _db

    _db.session.close()
    _db.drop_all()


@pytest.fixture(autouse=True)
def session(db, monkeypatch, request):
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection)
    session = db.create_scoped_session(options=options)
    monkeypatch.setattr(db, 'session', session)
    yield session
    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def client(app, db):
    with app.test_client() as client:
        yield client


@pytest.fixture
def survey_client(db, client):
    survey_parameters = {
        'email': 'test1_admin@email.com',
        'password': 'test123',
        'surveyName': 'TestSurvey',
        'signupCode': admin_db.token.new_survey.get_active().token
    }
    client.post('/v1/new',
                data=json.dumps(survey_parameters),
                content_type='application/json')
    yield client
