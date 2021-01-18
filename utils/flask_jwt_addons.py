#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017


def survey_instance_id(user):
    return user.survey.id


def survey_instance_name(user):
    return user.survey.pretty_name


def user_role_level(user):
    levels = {
        'admin': 0,
        'researcher': 1,
        'participant': 2
    }

    for r in user.roles:
        return levels[r.name]
