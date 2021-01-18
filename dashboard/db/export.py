#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
#
# Database functions for exporting full survey data to zip
import codecs
from datetime import datetime
from decimal import Decimal
from flask import current_app
import io
import logging
import os
import postgres_copy
import pytz
import unicodecsv as csv

import config
from models import db, CancelledPromptResponse, MobileUser, MobileCoordinate, PromptResponse
from utils.tripbreaker import algorithm as tripbreaker

from .mobile_user import MobileUserActions
from .survey import SurveyActions


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(config.DashboardConfig.APP_NAME)


def _utc_timestamp(timestamp):
    return timestamp.replace(microsecond=0).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')

def _epoch_timestamp(timestamp):
    epoch = datetime(1970, 1, 1, tzinfo=pytz.utc)
    timestamp_epoch = int((timestamp.astimezone(pytz.utc) - epoch).total_seconds())
    return timestamp_epoch

class ExportFormatters:
    @staticmethod
    def survey_responses_csv(survey, active_users, tz):
        # initialize output .csv file in memory with column headers
        responses_csv = io.BytesIO()
        responses_csv.write(codecs.BOM_UTF8)
        writer = csv.writer(responses_csv)

        location_column_types = [4, 105, 106, 107]
        location_columns = {}
        ignored_columns = ['survey_id']
        install_columns = []
        for c in MobileUser.__table__.columns:
            if c.name in ignored_columns:
                continue
            if c.type.python_type == datetime:
                install_columns.append(c.name + '_UTC')
                install_columns.append(c.name + '_epoch')
            else:
                install_columns.append(c.name)

        json_columns = []
        for q in survey.survey_questions.order_by('question_num'):
            if q.question_type in location_column_types:
                location_columns[q.question_label + '_lat'] = q.question_label
                location_columns[q.question_label + '_lon'] = q.question_label
                json_columns.append(q.question_label + '_lat')
                json_columns.append(q.question_label + '_lon')
            else:
                json_columns.append(q.question_label)
        headers = install_columns + json_columns
        writer.writerow(headers)
        
        # generate each .csv row from survey's active users and write to memory file
        for user in active_users:
            user.created_at_UTC = _utc_timestamp(user.created_at)
            user.created_at_epoch = _epoch_timestamp(user.created_at)
            user.modified_at_UTC = _utc_timestamp(user.modified_at)
            user.modified_at_epoch = _epoch_timestamp(user.modified_at)
            device_row = [getattr(user, col) for col in install_columns]
            survey_response = user.survey_response.one_or_none()

            json_row = []
            if survey_response:
                for col in json_columns:
                    if col in location_columns:
                        location_col = location_columns[col]
                        location = survey_response.response.get(location_col)
                        if location:
                            if col.endswith('_lat'):
                                json_row.append(location['latitude'])
                            elif col.endswith('_lon'):
                                json_row.append(location['longitude'])
                        else:
                            json_row.append('')    
                    elif col in survey_response.response:
                        response = survey_response.response[col]
                        if isinstance(response, list):
                            response = '; '.join(response)
                        json_row.append(response)
                    else:
                        json_row.append('')

            csv_row = device_row + json_row
            writer.writerow(csv_row)
        return responses_csv

    @staticmethod
    def coordinates_csv(survey, active_users, start, end):
        def _tz_formatters(table, cols):
            formatters = []
            for col_name in cols:
                col = getattr(table, col_name)
                timestamp = db.func.timezone('UTC', col).label('timestamp_UTC')
                timestamp_epoch = db.func.extract('epoch', col).cast(db.Integer).label('timestamp_epoch')
                formatters.append(timestamp)
                formatters.append(timestamp_epoch)
            return formatters

        coordinates_csv = io.BytesIO()
        coordinates_csv.write(codecs.BOM_UTF8)
        active_mobile_ids = [u.id for u in active_users]
        formatters = _tz_formatters(MobileCoordinate, ['timestamp'])
        coordinates = (db.session.query(MobileUser, MobileCoordinate, *formatters)
                       .join(MobileCoordinate)
                       .filter(db.and_(MobileCoordinate.mobile_id.in_(active_mobile_ids),
                                       MobileCoordinate.timestamp >= start,
                                       MobileCoordinate.timestamp <= end))
                       .options(db.Load(MobileUser).defer('id')
                                                   .load_only('uuid'),
                                db.Load(MobileCoordinate).defer('mobile_id')
                                                         .defer('survey_id')
                                                         .defer('timestamp'))
                       .order_by(MobileCoordinate.id))
        postgres_copy.copy_to(coordinates, coordinates_csv, db.engine,
                              format='csv', header=True)
        return coordinates_csv

    @staticmethod
    def prompts_csv(survey, active_users, start, end):
        prompts_csv = io.BytesIO()
        prompts_csv.write(codecs.BOM_UTF8)
        active_mobile_ids = [u.id for u in active_users]
        prompts = (db.session.query(MobileUser, PromptResponse)
                             .join(PromptResponse)
                             .filter(db.and_(PromptResponse.mobile_id.in_(active_mobile_ids)),
                                             PromptResponse.displayed_at >= start,
                                             PromptResponse.displayed_at <= end)
                             .order_by(PromptResponse.id))
        ignored_columns = ['survey_id', 'mobile_id']
        columns = []
        for c in PromptResponse.__table__.columns:
            if c.name in ignored_columns:
                continue
            if c.type.python_type == datetime:
                columns.append(c.name + '_UTC')
                columns.append(c.name + '_epoch')
            else:
                columns.append(c.name)

        # create csv file in memory with list responses expanded to string
        csv_writer = csv.writer(prompts_csv)
        headers = list(columns)
        headers.insert(1, 'uuid')
        csv_writer.writerow(headers)

        for user, prompt in prompts:
            prompt.displayed_at_UTC = _utc_timestamp(prompt.displayed_at)
            prompt.displayed_at_epoch = _epoch_timestamp(prompt.displayed_at)
            prompt.recorded_at_UTC = _utc_timestamp(prompt.recorded_at)
            prompt.recorded_at_epoch = _epoch_timestamp(prompt.recorded_at)
            prompt.edited_at_UTC = _utc_timestamp(prompt.edited_at)
            prompt.edited_at_epoch = _epoch_timestamp(prompt.edited_at)
            prompt_row = []
            for col in columns:
                # make uuid second column value
                if len(prompt_row) == 1:
                    prompt_row.append(user.uuid)

                value = getattr(prompt, col)
                if isinstance(value, list):
                    value = '; '.join([v.strip() for v in value])
                prompt_row.append(value)
            csv_writer.writerow(prompt_row)
        return prompts_csv

    @staticmethod
    def cancelled_prompts_csv(survey, active_users, start, end):
        cancelled_prompts_csv = io.BytesIO()
        cancelled_prompts_csv.write(codecs.BOM_UTF8)
        active_mobile_ids = [u.id for u in active_users]
        cancelled_prompts = (db.session.query(MobileUser, CancelledPromptResponse)
                                       .join(CancelledPromptResponse)
                                       .filter(db.and_(CancelledPromptResponse.mobile_id.in_(active_mobile_ids)),
                                                       CancelledPromptResponse.displayed_at >= start,
                                                       CancelledPromptResponse.displayed_at <= end)
                                       .order_by(CancelledPromptResponse.id))

        ignored_columns = ['survey_id', 'mobile_id']
        columns = []
        for c in CancelledPromptResponse.__table__.columns:
            if c.name in ignored_columns:
                continue
            if c.type.python_type == datetime:
                columns.append(c.name + '_UTC')
                columns.append(c.name + '_epoch')
            else:
                columns.append(c.name)

        # create csv file in memory with list responses expanded to string
        csv_writer = csv.writer(cancelled_prompts_csv)
        headers = list(columns)
        headers.insert(1, 'uuid')
        csv_writer.writerow(headers)

        for user, cancelled in cancelled_prompts:
            cancelled.displayed_at_UTC = _utc_timestamp(cancelled.displayed_at)
            cancelled.displayed_at_epoch = _epoch_timestamp(cancelled.displayed_at)
            if cancelled.cancelled_at:
                cancelled.cancelled_at_UTC = _utc_timestamp(cancelled.cancelled_at)
                cancelled.cancelled_at_epoch = _epoch_timestamp(cancelled.cancelled_at)
            else:
                cancelled.cancelled_at_UTC = None
                cancelled.cancelled_at_epoch = None
            cancelled_row = []
            for col in columns:
                # make uuid second column value
                if len(cancelled_row) == 1:
                    cancelled_row.append(user.uuid)
                cancelled_row.append(getattr(cancelled, col))
            csv_writer.writerow(cancelled_row)
        return cancelled_prompts_csv

    @staticmethod
    def trips_csv(survey, active_users, start, end):
        def _process_trip_points(uuid, points, headers):
            rows = []
            for pt in points:
                pt_row = [uuid]
                for h in headers:
                    if h == 'uuid':
                        continue

                    value = pt.get(h)
                    if h == 'timestamp_UTC':
                        value = _utc_timestamp(pt['timestamp'])
                    elif h == 'timestamp_epoch':
                        value = _epoch_timestamp(pt['timestamp'])
                    elif isinstance(value, Decimal):
                        value = float(value)
                    pt_row.append(value)
                rows.append(pt_row)
            return rows

        parameters = {
            'break_interval_seconds': survey.trip_break_interval,
            'subway_buffer_meters': survey.trip_subway_buffer,
            'cold_start_distance_meters': survey.trip_break_cold_start_distance,
            'accuracy_cutoff_meters': survey.gps_accuracy_threshold
        }
        trips_csv = io.BytesIO()
        trips_csv.write(codecs.BOM_UTF8)
        writer = csv.writer(trips_csv)
        headers = ['uuid', 'trip', 'latitude', 'longitude', 'h_accuracy', 'timestamp_UTC',
                   'timestamp_epoch', 'trip_distance', 'distance', 'break_period', 'trip_code']

        writer.writerow(headers)
        for user in active_users:
            user_coordinates = (user.mobile_coordinates
                                          .filter(db.and_(MobileCoordinate.timestamp >= start,
                                                          MobileCoordinate.timestamp <= end)))

            trips, segments = tripbreaker.run(parameters,
                                              survey.subway_stops,
                                              user_coordinates)

            for trip_id, points in trips.iteritems():
                point_rows = _process_trip_points(user.uuid, points, headers)
                writer.writerows(point_rows)
        return trips_csv


class ExportActions:
    def __init__(self):
        self.mobile_user = MobileUserActions()
        self.formatters = ExportFormatters()
        self.survey = SurveyActions()

    # remove the previous survey export from assets directory by filename
    def cleanup_stale_data(self, export_type, export_info, basepath):
        if export_info.get(export_type) and export_info[export_type].get('uri'):
            # remove previous export if exists
            filename = export_info[export_type]['uri'].split('/')[-1]
            existing_fp = os.path.join(
                current_app.config['ASSETS_FOLDER'],
                basepath, filename
            )
            if os.path.exists(existing_fp):
                os.remove(existing_fp)

    # update survey with export start, end, and requested datetimes
    def _begin(self, export_type, survey, basepath, start, end):
        export = survey.last_export
        if not isinstance(export, dict):
            export = {'raw': {}, 'trips': {}}
        else:
            self.cleanup_stale_data(export_type, export, basepath)

        export[export_type] = {
            'export_start': start.isoformat(),
            'export_end': end.isoformat(),
            'export_time': datetime.utcnow().isoformat(),
            'exporting': True,
            'uri': None
        }

        survey.last_export = export
        db.session.add(survey)
        db.session.commit()

    # update database with export finished info
    def _finish(self, export_type, survey, basepath, filename):
        export = survey.last_export
        uri = os.path.join(current_app.config['ASSETS_ROUTE'],
                           basepath, filename)

        export[export_type].update({
            'exporting': False,
            'uri': uri})
        export.update({export_type: export[export_type]})
        survey.last_export = export
        db.session.add(survey)
        db.session.commit()
        return export

    def survey_data(self, survey, start, end, timezone):
        tz = pytz.timezone(timezone)
        active_users = [u for u in self.survey.get_active_users(survey, start, end)]
        responses_csv = self.formatters.survey_responses_csv(survey, active_users, tz)
        coordinates_csv = self.formatters.coordinates_csv(survey, active_users, start, end)
        prompts_csv = self.formatters.prompts_csv(survey, active_users, start, end)
        cancelled_prompts_csv = self.formatters.cancelled_prompts_csv(survey, active_users, start, end)

        return {
            'survey_responses.csv': responses_csv,
            'coordinates.csv': coordinates_csv,
            'prompt_responses.csv': prompts_csv,
            'cancelled_prompts.csv': cancelled_prompts_csv
        }

    def trips_data(self, survey, start, end, timezone):
        active_users = self.survey.get_active_users(survey, start, end)
        trips_csv = self.formatters.trips_csv(survey, active_users, start, end)
        filename = 'trips_{}.csv'.format(start.strftime('%Y%m%d'))
        return {filename: trips_csv}
