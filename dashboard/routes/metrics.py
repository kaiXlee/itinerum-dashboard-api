#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from collections import Counter
from dateutil import rrule
from datetime import datetime, timedelta
from flask import request
from flask_restful import Resource
from flask_security import roles_accepted
import logging
import pytz
from Queue import Queue
from threading import Thread

import config
from dashboard.database import Database
from utils.data import to_english
from utils.flask_jwt import jwt_required, current_identity
from utils.responses import Success


database = Database()
logger = logging.getLogger(config.DashboardConfig.APP_NAME)


def survey_overview(survey):
    def _get_count(count, queue):
        key, func = count
        queue.put((key, func.count()))

    start_15min = datetime.now(pytz.utc) - timedelta(minutes=15)
    start_24hr = datetime.now(pytz.utc) - timedelta(days=1)

    # perform counts in parallel with threads
    counts = [
        ('signups24hr', database.metrics.signups(survey, start_24hr)),
        ('activeUsers15min', database.metrics.active_users(survey, start_15min)),
        ('activeUsers24hr', database.metrics.active_users(survey, start_24hr)),
        ('numPoints24hr', database.metrics.recent_points(survey, start_24hr))
    ]

    queue = Queue()
    threads = []
    for count in counts:
        worker = Thread(target=_get_count, args=(count, queue))
        worker.setDaemon(True)
        worker.start()
        threads.append(worker)

    for t in threads:
        t.join()

    results = {}
    while not queue.empty():
        key, value = queue.get()
        results[key] = value

    logging.info(results)
    count_error_msg = 'Could not determine count.'
    response = [{
        'name': 'metrics.statsTable.signups24hr',
        'value': results.get('signups24hr', count_error_msg)
    }, {
        'name': 'metrics.statsTable.activeUsers15min',
        'value': results.get('activeUsers15min', count_error_msg)
    }, {
        'name': 'metrics.statsTable.activeUsers24hr',
        'value': results.get('activeUsers24hr', count_error_msg)
    }, {
        'name': 'metrics.statsTable.numPoints24hr',
        'value': results.get('numPoints24hr', count_error_msg)
    }]
    return response


# return the number of active users over the past day grouped by hour
def active_users_linegraph(survey):
    end = datetime.now(pytz.utc)
    start_24hr = end - timedelta(days=1)
    binned_active_users = database.metrics.hourly_active_users(survey, start_24hr, end)
    return binned_active_users


# fetch the signup datetime for each user in survey
def mobile_installations_bargraph(survey, start, end, period):
    signups = sorted([user.created_at for user in
                      database.metrics.signups(survey, start)])
    labels = []
    data = []
    if signups:
        start, end = signups[0], signups[-1]

        if period == 'days':
            daily_count = Counter()
            for dt in signups:
                timestamp = dt.strftime('%Y-%m-%d')
                daily_count[timestamp] += 1

            for dt in rrule.rrule(rrule.DAILY, dtstart=start, until=end):
                timestamp = dt.strftime('%Y-%m-%d')
                labels.append(timestamp)
                data.append(daily_count[timestamp])

        elif period == 'weeks':
            weekly_count = Counter()
            for timestamp in signups:
                year, week, _ = timestamp.isocalendar()
                weekly_count[(year, week)] += 1

            # iterate daterange to interpolate labels from start to end date
            for dt in rrule.rrule(rrule.WEEKLY, dtstart=start, until=end):
                year, week, _ = dt.isocalendar()
                label = '{year}, Week {week}'.format(week=week, year=year)
                labels.append(label)
                data.append(weekly_count[(year, week)])

        elif period == 'months':
            monthly_count = Counter()
            for dt in signups:
                timestamp = dt.strftime('%Y-%m')
                monthly_count[timestamp] += 1

            for dt in rrule.rrule(rrule.MONTHLY, dtstart=start, until=end):
                timestamp = dt.strftime('%Y-%m')
                labels.append(timestamp)
                data.append(monthly_count[timestamp])
    return {
        'labels': labels, 
        'datasets': [{
            'data': data
        }]
    }


class MetricsSurveyOverviewRoute(Resource):
    headers = {'Location': '/itinerum/metrics'}
    resource_type = 'MetricsSurveyOverview'

    @jwt_required()
    @roles_accepted('admin', 'researcher')
    def get(self):
        survey = database.survey.get(current_identity.survey_id)
        start = request.values.get('start')
        end = request.values.get('end')
        period = request.values.get('period')
        get_counts_overview = request.values.get('countsTable').lower() == 'true'
        response = {
            'installationsBarGraph': mobile_installations_bargraph(survey, start, end, period),
            'activeUsersLineGraph': active_users_linegraph(survey)
        }
        if get_counts_overview is True:
            response['overview'] = survey_overview(survey)

        return Success(status_code=200,
                       headers=self.headers,
                       resource_type=self.resource_type,
                       body=response)
