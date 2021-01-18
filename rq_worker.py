#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from flask_rq2 import RQ

from dashboard.server import create_app

app = create_app()
rq = RQ(app)

with app.app_context():
    print('RQ data exporter running on: {}'.format(app.config['RQ_REDIS_URL']))
    default_worker = rq.get_worker('default')
    default_worker.work()
