#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
#
# Database functions for dashboard surveys
from flask import current_app
from sqlalchemy.exc import IntegrityError, ProgrammingError

from models import (db, MobileCoordinate, MobileUser, NewSurveyToken, Survey,
                    SurveyQuestion, SurveyResponse, SurveyQuestionChoice,
                    SubwayStop, WebUserRole, web_user_role_lookup)
from hardcoded_survey_questions import default_stack


class SurveyActions(object):
    # update questions for a given survey by replacement; delete all existing
    # and append full new data to hardcoded questions
    def _replace_survey_questions(self, survey, questions):
        # remove old survey questions
        survey.survey_questions.delete(synchronize_session=False)
        db.session.flush()

        # load hardcoded default questions to new survey
        for question_index, question in enumerate(questions):
            survey_question = SurveyQuestion(
                survey_id=survey.id,
                question_num=question_index,
                question_type=question['id'],
                question_label=question['colName'],
                question_text=question['prompt'],
                answer_required=question['answerRequired']
            )

            for field_name, field_value in question['fields'].items():
                # ignore non-english (default) field names
                if 'choices_' in field_name:
                    continue

                if field_name == 'choices':
                    # use integer (list index) value for hardcoded
                    # question responses instead of text-values (iOS app request);
                    # this has a reciprocal reverse-lookup in the mobile api
                    if question['id'] >= 100:
                        for choice_index, choice_text in enumerate(field_value):
                            question_choice = SurveyQuestionChoice(
                                choice_num=choice_index,
                                choice_text=choice_index,
                                choice_field='option')
                            survey_question.choices.append(question_choice)
                    else:
                        for choice_index, choice_text in enumerate(field_value):
                            question_choice = SurveyQuestionChoice(
                                choice_num=choice_index,
                                choice_text=choice_text,
                                choice_field='option')
                            survey_question.choices.append(question_choice)
                else:
                    question_choice = SurveyQuestionChoice(
                        choice_num=None,
                        choice_text=field_value,
                        choice_field=field_name)
                    survey_question.choices.append(question_choice)
            db.session.add(survey_question)
        db.session.commit()

    # return a survey record by id
    def get(self, survey_id):
        return Survey.query.get(survey_id)

    # return all the users with coordinates existing between the given time bounds
    def get_active_users(self, survey, start, end):
        users = (survey.mobile_users.join(MobileCoordinate)
                                    .filter(db.and_(MobileCoordinate.timestamp >= start,
                                                    MobileCoordinate.timestamp <= end))
                                    .group_by(MobileUser.id)
                                    .order_by(MobileUser.id))
        return users

    # return the admin user record for a survey record
    def get_admin(self, survey):
        query = (survey.web_users.join(web_user_role_lookup)
                                 .join(WebUserRole)
                                 .filter_by(name='admin'))
        return query.one_or_none()

    # return the time of the first collected coordinate in a survey 
    # indicating data collection has begun
    def get_start_time(self, survey):
        min_datetime = current_app.config['MINIMUM_DATETIME']
        result = (survey.mobile_coordinates.filter(MobileCoordinate.timestamp >= min_datetime)
                                           .order_by(MobileCoordinate.timestamp.asc())
                                           .first())
        if result:
            return result.timestamp

    # TO DO: remove, seems to mimic `get_start_time` but worse
    def has_started__deprecated(self, survey):
        if survey.survey_responses.first():
            return True
        return False

    # return a survey by its normalized lowercase name
    def find_by_name(self, name):
        return Survey.query.filter_by(name=name.lower()).one_or_none()

    # return the survey questions as JSON for downloading schemas
    def get_survey_questions_json(self, survey):
        json_questions = []
        for question in survey.survey_questions.order_by(SurveyQuestion.question_num):
            element = {
                'id': question.question_type,
                'prompt': question.question_text,
                'fields': {},
                'colName': question.question_label,
                'answerRequired': question.answer_required
            }
            choices_are_ordered = all([c.choice_num is not None for c in question.choices])
            if choices_are_ordered:
                for choice in sorted(question.choices, key=lambda q: q.choice_num):
                    if choice.choice_field == 'option':
                        element['fields'].setdefault('choices', []).append(choice.choice_text)
                    else:
                        element['fields'][choice.choice_field] = choice.choice_text
            json_questions.append(element)
        return json_questions

    # resets all the collected information for a given survey; questions,
    # prompts, and settings will persist
    def reset(self, survey):
        survey.mobile_users.delete()
        survey.last_export = {'raw': {}, 'trips': {}}
        db.session.commit()

    # general update function to edit survey settings, questions
    # TO DO: what about prompts?
    def update(self, survey, settings=None, questions=None):
        if settings:
            for key, value in settings.items():
                setattr(survey, key, value)
        if questions is not None:
            self._replace_survey_questions(survey, questions)
        db.session.add(survey)
        db.session.commit()

    # adds subway locations to the stops table for use with tripbreaker
    def upsert_subway_stops(self, survey, stops):
        survey.subway_stops.delete()

        subway_stops = []
        for stop in stops:
            s = SubwayStop(survey_id=survey.id,
                           latitude=stop['latitude'],
                           longitude=stop['longitude'])
            subway_stops.append(s)
        db.session.bulk_save_objects(subway_stops)
        db.session.commit()
        return subway_stops


class RegisterSurveyActions(SurveyActions):
    def __init__(self):
        super(RegisterSurveyActions, self).__init__()

    def _generate_multicolumn_index(self, survey):
        # since index is not declared within models.py,
        # do not create during testing since it will interfere with
        # db.create_all() and db.drop_app() commands in pytest fixture
        if current_app.config['CONF'] == 'testing':
            return

        searchable_field_ids = (1, 2, 3, 5, 6, 100, 101, 102,
                                103, 104, 108, 109, 110, 111)
        query = survey.survey_questions
        answers_columns = [q.question_label for q in query.all()
                           if q.question_type in searchable_field_ids]

        if answers_columns:
            try:
                idx_name = 'survey{}_multi_idx'.format(survey.id)
                query = '''DROP INDEX {idx};'''.format(idx=idx_name)
                db.engine.execution_options(autocommit=True).execute(query)
            except ProgrammingError:
                # safely ignore error about index not already existing
                pass

            # create a new multi-index for full-text search
            index_fields = []
            for col in answers_columns:
                index_fields.append(db.func.lower(SurveyResponse.response[col].astext))

            new_index = db.Index('survey{}_multi_idx'.format(survey.id), *index_fields)
            new_index.create(bind=db.engine)
            db.session.commit()

    # adds a new survey to database with default hardcoded questions
    # and returns the survey object if successful
    def create(self, survey_name):
        survey = Survey(name=survey_name.lower(),
                        pretty_name=survey_name,
                        language='en')
        db.session.add(survey)

        try:
            db.session.flush()
            self._replace_survey_questions(survey=survey, questions=default_stack)
            self._generate_multicolumn_index(survey)
            db.session.commit()
            return survey
        except IntegrityError:
            db.session.rollback()

    # checks that a token is valid for registering a new survey instance
    def validate_token(self, token):
        existing_token = NewSurveyToken.query.filter_by(token=token).one_or_none()
        if existing_token and existing_token.active:
            return existing_token

    # increments the usage counter when a new survey is registered
    def use_token(self, token):
        valid_token = self.validate_token(token)
        if valid_token:
            valid_token.usages += 1
            try:
                db.session.commit()
                return valid_token
            except:
                db.session.rollback()

