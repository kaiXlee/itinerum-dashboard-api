#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from datetime import timedelta
from faker import Factory
import random
import pytz

fake = Factory.create()


def generate_installation(survey_name):
    tz = pytz.timezone('America/Montreal')
    fake_dt = tz.localize(fake.date_time_between(start_date='-3d', end_date='now')).isoformat()
    new_install_data = {
        'uuid': fake.uuid4(),
        'model': 'iPhone 4s',
        'itinerum_version': '99c',
        'os': 'ios' if fake.pybool() else 'android',
        'os_version': str(fake.pydecimal(left_digits=2, right_digits=2, positive=True)),
        'created_at': fake_dt
    }
    return new_install_data


def generate_survey_answers(uuid, schema):
    def choose_selection(question):
        choice = random.choice(question['fields']['choices'])
        return choice
    def choose_selections(question):
        choices = question['fields']['choices']
        num_of_selections = random.randint(0, len(choices))
        selections = []
        for i in range(num_of_selections):
            selections.append(random.choice(choices))
        return selections
    def choose_number(question):
        return fake.pyint()
    def choose_address(question):
        latitude = str(fake.latitude())
        longitude = str(fake.longitude())
        return { 'latitude': latitude, 'longitude': longitude }
    def choose_email(question):
        return fake.email()
    def choose_text(question):
        return fake.text()
    def skip(question):
        return
    def choose_boolean(question):
        return random.choice([True, False])

    fn = {
        1: choose_selection,
        2: choose_selections,
        3: choose_number,
        4: choose_address,
        5: choose_text,
        98: choose_boolean,  # tos
        99: skip,            # page break
        100: choose_selection,
        101: choose_selection,
        102: choose_selection,
        103: choose_email,
        104: choose_selection,
        105: choose_address,
        106: choose_address,
        107: choose_address,
        108: choose_selection,
        109: choose_selection,
        110: choose_selection,
        111: choose_selection
    }

    test_data = {
        'uuid': uuid,
        'survey': {},
    }

    user_type = random.choice(['student', 'worker', 'both'])
    if user_type is 'student':
        ignore_ids = [107, 110, 111]
    elif user_type is 'worker':
        ignore_ids = [106, 108, 109]
    else:
        ignore_ids = []

    # answer user supplied questions
    for question in schema:
        question_id = question['id']
        if question_id in ignore_ids:
            continue

        col_name = question['colName']
        test_data['survey'][col_name] = fn[question_id](question)
    return test_data


def generate_coordinates(uuid, n=0):
    coordinates = []
    tz = pytz.timezone('America/Montreal')
    fake_dt = tz.localize(fake.date_time_between(start_date='-3d', end_date='-1s'))
    for i in range(n):
        coordinates.append({
            'latitude': str(45.45 + random.random()/10),
            'longitude': str(-73.55 - random.random()/10),
            'speed': random.uniform(0, 60),
            'v_accuracy': random.randint(0, 35),
            'h_accuracy': random.randint(0, 35),
            'acceleration_x': random.random(),
            'acceleration_y': random.random(),
            'acceleration_z': random.random(),
            'mode_detected': random.randint(1, 5),
            'timestamp': fake_dt.isoformat()
        })
        fake_dt += timedelta(seconds=15)
    return coordinates


def generate_prompts_answers(uuid, prompts):
    answers = []
    tz = pytz.timezone('America/Montreal')
    for prompt in prompts:
        fake_dt = fake.date_time_between(start_date='-3d', end_date='now')
        answers.append({
            'prompt': prompt['prompt'],
            'answer': random.choice(prompt['choices']),
            'timestamp': tz.localize(fake_dt).isoformat(),
            'recorded_at': tz.localize(fake_dt).isoformat(),
            'latitude': str(45.45 + random.random()/10),
            'longitude': str(-73.55 - random.random()/10)
        })
    return answers


# insert fake data into mobile database
def insert_fake_data(database, survey_name, users=10):
    for user in range(users):
        survey = database.survey.find_by_name(survey_name.lower())

        # /create route
        install_data = generate_installation(survey_name)
        user = database.user.create(survey=survey, user_data=install_data)

        # /update route
        survey_json = database.survey.formatted_survey_questions(survey)
        survey_data = generate_survey_answers(uuid=install_data['uuid'],
                                              schema=survey_json)
        database.survey.upsert(user=user, answers=survey_data)

        coordinates_data = generate_coordinates(uuid=install_data['uuid'], n=50)
        database.coordinates.insert(user=user, coordinates=coordinates_data)

        prompts_json = database.survey.formatted_survey_prompts(survey)
        prompts_data = generate_prompts_answers(uuid=install_data['uuid'],
                                                prompts=prompts_json)
        database.prompts.insert(user=user, prompts=prompts_data)

