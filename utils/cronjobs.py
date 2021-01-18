#!/usr/bin/env python
# Kyle Fitzsimmons, 2017
#
# Celery worker cronjobs
from celery import Celery
from celery.task.schedules import crontab
from celery.decorators import periodic_task
import os
import time

celery = Celery('bulkdata')


# clean-up data export directory every 5 minutes of dashboard bulk downloads
@periodic_task(run_every=crontab(minute='*/5'))
def cleanup_files_dir():
    expiry = 24 * 60 * 60
    now = time.time()
    for filename in os.listdir(CONF.OUTPUT_DIR):
        path = os.path.join(CONF.OUTPUT_DIR, filename)
        if path.endswith('.zip'):
            age = now - os.path.getmtime(path)
            if age > expiry:
                os.remove(filename)
