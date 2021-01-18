#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
#
# Database functions for dashboard users
from datetime import timedelta
from models import db, MobileCoordinate, MobileUser, SurveyResponse


class MetricsActions:
    def signups(self, survey, start):
        return survey.mobile_users.filter(MobileUser.created_at >= start)

    def responses(self, survey, start):
        query = (SurveyResponse.query
                               .join(MobileUser, SurveyResponse.mobile_id == MobileUser.id)
                               .filter(MobileUser.created_at >= start)
                               .filter(SurveyResponse.survey_id == survey.id))
        return query

    def active_users(self, survey, start):
        return (survey.mobile_coordinates.filter(MobileCoordinate.timestamp >= start)
                                         .distinct(MobileCoordinate.mobile_id))

    def hourly_active_users(self, survey, start, end):
        # create intervals for each hour between the start and end dates (inclusive)
        start_floor = start.replace(minute=0, second=0, microsecond=0)
        end_ceiling = end.replace(minute=0, second=0, microsecond=0)
        end_ceiling += timedelta(hours=1)

        interval_min = start_floor
        interval_max = start_floor + timedelta(hours=1)
        hourly_counts = {}
        while interval_max <= end_ceiling:
            hourly_counts[interval_min.isoformat()] = 0
            interval_min += timedelta(hours=1)
            interval_max += timedelta(hours=1)

        counts_query = (db.session.query(db.func.date_trunc('hour', MobileCoordinate.timestamp), db.func.count(db.func.distinct(MobileCoordinate.mobile_id)))
                                  .filter(MobileCoordinate.timestamp >= start_floor, MobileCoordinate.survey_id == survey.id)
                                  .group_by(db.func.date_trunc('hour', MobileCoordinate.timestamp)))

        for timestamp, users_count in counts_query:
            iso_timestamp = timestamp.isoformat()
            hourly_counts[iso_timestamp] = users_count
        hourly_counts = [(t, hourly_counts[t]) for t in sorted(hourly_counts)]
        return hourly_counts

    def recent_points(self, survey, start):
        return survey.mobile_coordinates.filter(MobileCoordinate.timestamp >= start)
