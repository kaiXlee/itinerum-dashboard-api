#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
#
# Database functions for mobile app users
from models import (db, CancelledPromptResponse, MobileCoordinate, MobileUser,
                    PromptResponse, SurveyQuestion, SurveyResponse)
from utils.data import flatten_dict


class MobileUserActions:
    def find_by_email(self, email):
        response = SurveyResponse.query.filter(
            SurveyResponse.response['Email'].astext == email).one_or_none()
        if response:
            return response.mobile_user

    # generate a double-sided search filter for each column in a normalized sql table
    @staticmethod
    def _normalized_filters(table, search, ignore=[], cast=[]):
        filters = []
        for column in table.__table__.columns:
            if column.name in ignore:
                continue
            if column.name in cast:
                filters.append(db.cast(column, db.String).contains(search))
            else:
                filters.append(db.func.lower(column).contains(search))
        return filters

    # return a left-to-right search filter in each column of a JSON(B) postgres table
    @staticmethod
    def _denormalized_filters(columns, search):
        filters = [SurveyResponse.response[field].astext.ilike(search + '%')
                   for field in columns]
        return filters

    # remove unwanted fields and cast datetimes to string
    @staticmethod
    def _format_users_rows(rows, ignore=[], datetime_cast=[]):
        formatted = []
        for row in rows:
            data = row.mobile_user.__dict__
            data.update(row.response)

            cleaned = {}
            for key, value in data.items():
                if key in datetime_cast:
                    cleaned[key] = value.isoformat()
                elif key in ignore:
                    pass
                elif isinstance(value, dict):
                    flattened = flatten_dict(value, parent_key=key, sep='.')
                    cleaned.update(flattened)
                else:
                    cleaned[key] = value

            formatted.append(cleaned)
        return formatted

    def paginated_table(self, survey, page_index=0, items_per_page=10,
                        search=None, sort_fields={}):
        # return empty response if no user rows found
        if not survey.survey_responses.first():
            return {
                'data': [],
                'pagination': {
                    'currentPage': 0,
                    'totalPages': 0,
                    'totalItems': 0
                },
                'columns': []
            }

        # generate table columns
        excluded_cols = ['id', 'survey_id', 'modified_at']
        columns = [c.name for c in MobileUser.__table__.columns
                   if c.name not in excluded_cols]

        # select column names from survey stack excluding address fields
        excluded_types = [4, 105, 106, 107]  # address prompts
        json_columns = [q.question_label for q 
                        in survey.survey_questions.order_by(SurveyQuestion.question_num)
                        if q.question_type not in excluded_types]
        columns += json_columns

        # begin building the query
        query = survey.survey_responses.join(MobileUser)

        # generate the search string filter on each field and cast
        # column to text if necessary
        cast = ['created_at']
        ignore = ['_sa_instance_state', 'id', 'survey_id', 'modified_at']
        search_filters = []
        if search:
            search_filters += self._normalized_filters(MobileUser, search, ignore, cast)
            search_filters += self._denormalized_filters(json_columns, search)
            query = query.filter(db.or_(*search_filters))

        if sort_fields:
            field_is_json = sort_fields['column'] in json_columns
            if field_is_json:
                column = SurveyResponse.response[sort_fields['column']]
            else:
                column = getattr(MobileUser, sort_fields['column'])

            if sort_fields['direction'] == -1:
                column = column.desc()
            query = query.order_by(column)

        # create the sliced pagination query
        paginated_query = query.paginate(page_index, items_per_page)

        # format output rows for javascript table
        rows = self._format_users_rows(paginated_query.items, ignore, cast)

        # create output pagination json object
        total_answers = survey.survey_responses.count()
        total_pages = total_answers / items_per_page
        if total_answers > 0 and items_per_page != 0:
            total_pages += 1

        response = {
            'data': rows,
            'pagination': {
                'currentPage': page_index,
                'totalPages': total_pages,
                'totalItems': total_answers
            },
            'columns': columns
        }
        return response

    def active_period(self, survey, uuid):
        user = survey.mobile_users.filter_by(uuid=uuid).one_or_none()
        if user:
            first_points = (user.mobile_coordinates
                                .order_by(MobileCoordinate.timestamp.asc())
                                .limit(50))
            # test to remove error rows with all 0-values (iOS bug)
            for row in first_points:
                if not (row.latitude == 0 and row.longitude == 0):
                    first = row
                    last = (user.mobile_coordinates
                                .order_by(MobileCoordinate.timestamp.desc())
                                .first())
                    return first.timestamp, last.timestamp
        return None, None

    def coordinates(self, survey, uuid, start_time=None,
                    end_time=None, limit=None, min_accuracy=100):
        user = survey.mobile_users.filter_by(uuid=uuid).one_or_none()
        if user:
            results = user.mobile_coordinates.filter(
                MobileCoordinate.h_accuracy <= min_accuracy)
            if start_time and end_time:
                results = results.filter(db.and_(
                    MobileCoordinate.timestamp >= start_time,
                    MobileCoordinate.timestamp <= end_time))
            # get the most recent points
            return results.order_by(MobileCoordinate.timestamp.asc()).limit(limit)

    def prompt_responses(self, survey, uuid, start_time=None, end_time=None):
        user = survey.mobile_users.filter_by(uuid=uuid).one_or_none()
        if user:
            results = user.prompt_responses
            if start_time and end_time:
                results = results.filter(db.and_(
                    PromptResponse.displayed_at >= start_time,
                    PromptResponse.displayed_at <= end_time))
            return results.order_by(PromptResponse.displayed_at.asc())

    def cancelled_prompts(self, survey, uuid, start_time=None, end_time=None):
        user = survey.mobile_users.filter_by(uuid=uuid).one_or_none()
        if user:
            results = user.cancelled_prompts
            if start_time and end_time:
                results = results.filter(db.and_(
                    CancelledPromptResponse.displayed_at >= start_time,
                    CancelledPromptResponse.displayed_at <= end_time))
            return results.order_by(CancelledPromptResponse.displayed_at.asc())
