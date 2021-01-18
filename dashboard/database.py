#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
#
# Dashboard SQL database wrapper
from dashboard.db import mobile_user, export, metrics, prompts, survey, web_user


class Database:
    def __init__(self):
        self.export = export.ExportActions()
        self.mobile_user = mobile_user.MobileUserActions()
        self.prompts = prompts.PromptsActions()
        self.survey = survey.SurveyActions()
        self.survey.register = survey.RegisterSurveyActions()
        self.metrics = metrics.MetricsActions()
        self.web_user = web_user.WebUserActions()
