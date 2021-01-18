#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
#
# Database functions for dashboard users
from flask import current_app
from flask_security.utils import encrypt_password
import math
from sqlalchemy.exc import IntegrityError

from models import db, user_datastore, ResearcherInviteToken, WebUser, WebUserResetPasswordToken
from utils.tokens import generate_registration_token, validate_registration_token


class WebUserActions:
    def get_user_role(self, role):
        return user_datastore.find_or_create_role(name=role)

    def find_by_email(self, email):
        return WebUser.query.filter_by(email=email).one_or_none()

    def get_invite_researcher_token(self, survey):
        return survey.researcher_invite_token.filter_by(active=True).one_or_none()

    def create_invite_researcher_token(self, survey):
        existing = self.get_invite_researcher_token(survey)
        if existing:
            existing.active = False
            db.session.flush()
        new_token_str = generate_registration_token(salt=current_app.config['SECURITY_PASSWORD_SALT'])
        new_token = ResearcherInviteToken(survey_id=survey.id,
                                          token=new_token_str,
                                          active=True)
        db.session.add(new_token)
        db.session.commit()
        return new_token

    def get_reset_password_token(self, web_user):
        return web_user.reset_password_token.filter_by(active=True).one_or_none()

    def create_reset_password_token(self, email):
        web_user = self.find_by_email(email)
        if web_user:
            existing = self.get_reset_password_token(web_user)
            if existing:
                existing.active = False
                db.session.flush()
            new_token_str = generate_registration_token(salt=current_app.config['SECURITY_PASSWORD_SALT'],
                                                        min_length=60)
            new_token = WebUserResetPasswordToken(web_user_id=web_user.id,
                                                  token=new_token_str)
            db.session.add(new_token)
            db.session.commit()
            return new_token

    def update_password(self, email, password, token):
        user = self.find_by_email(email)
        active_token = WebUserResetPasswordToken.query.filter_by(token=token, active=True).one_or_none()
        if user and active_token:
            user.password = encrypt_password(password)
            active_token.active = False
            db.session.commit()
            return user

    def create_admin(self, survey, email, password):
        admin_role = self.get_user_role('admin')
        user = user_datastore.create_user(
            email=email,
            password=encrypt_password(password),
            survey_id=survey.id)
        user_datastore.add_role_to_user(user, admin_role)
        try:
            db.session.commit()
            return user
        except IntegrityError:
            db.session.rollback()

    def create_researcher(self, survey, email, password, token):
        existing = ResearcherInviteToken.query.filter_by(token=token).one_or_none()
        if existing and validate_registration_token(token=token,
                                                    salt=current_app.config['SECURITY_PASSWORD_SALT'],
                                                    expiration=current_app.config['SIGNUP_EXPIRATION']):
            existing.usages += 1
            researcher_role = self.get_user_role('researcher')
            user = user_datastore.create_user(
                email=email,
                password=encrypt_password(password),
                survey_id=survey.id)
            user_datastore.add_role_to_user(user, researcher_role)
            try:
                db.session.commit()
                return user
            except IntegrityError:
                db.session.rollback()
                return False

    def create_participant(self, survey, email, password, uuid):
        participant_role = self.get_user_role('participant')
        user = user_datastore.create_user(
            email=email,
            password=encrypt_password(password),
            survey_id=survey.id,
            participant_uuid=uuid)
        user_datastore.add_role_to_user(user, participant_role)
        try:
            db.session.commit()
            return user
        except IntegrityError:
            db.session.rollback()
            return False

    def delete(self, web_user):
        user_datastore.delete(web_user)
        db.session.commit()

    def paginated_table(self, survey, page_index=0, items_per_page=10, sort_fields={}):
        query = survey.web_users

        if sort_fields:
            column = getattr(WebUser, sort_fields['column'])
            if sort_fields['direction'] == -1:
                column = column.desc()
            query = query.order_by(column)

        # create the sliced pagination query
        paginated_rows = []
        for user in query.paginate(page_index, items_per_page).items:
            user_level = [r.name for r in user.roles][0]
            paginated_rows.append({
                'email': user.email,
                'createdAt': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'active': user.active,
                'userLevel': user_level
            })

        # create output pagination json object
        total_answers = query.count()
        total_pages = int(math.ceil(float(total_answers) / items_per_page))

        response = {
            'data': paginated_rows,
            'pagination': {
                'currentPage': page_index,
                'totalPages': total_pages,
                'totalItems': total_answers
            }
        }
        return response
