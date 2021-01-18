#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
#
# Database functions for mobile prompts
from models import db, PromptQuestion, PromptQuestionChoice


class PromptsActions:
    def _replace_prompt_questions(self, survey, prompts):
        # clear old prompts
        survey.prompt_questions.delete(synchronize_session=False)

        # add prompts to prompts tables
        for prompt_index, prompt in enumerate(prompts):
            stack_prompt = PromptQuestion(
                survey_id=survey.id,
                prompt_num=prompt_index,
                prompt_type=prompt['id'],
                prompt_label=prompt['colName'],
                prompt_text=prompt['prompt'],
                answer_required=prompt['answerRequired']
            )

            for field_name, field_value in prompt['fields'].items():
                for choice_index, choice_text in enumerate(field_value):
                    stack_choice = PromptQuestionChoice(
                        choice_num=choice_index,
                        choice_text=choice_text,
                        choice_field='option'
                    )
                    stack_prompt.choices.append(stack_choice)
            db.session.add(stack_prompt)

    def update(self, survey, prompts=None):
        if isinstance(prompts, list):
            self._replace_prompt_questions(survey, prompts)
        db.session.add(survey)
        db.session.commit()

    def formatted_prompt_questions(self, survey):
        json_prompts = []
        for prompt in survey.prompt_questions.order_by(PromptQuestion.prompt_num):
            element = {
                'id': prompt.prompt_type,
                'prompt': prompt.prompt_text,
                'fields': {},
                'colName': prompt.prompt_label,
                'answerRequired': prompt.answer_required
            }

            for choice in sorted(prompt.choices, key=lambda p: p.choice_num):
                if choice.choice_field == 'option':
                    element['fields'].setdefault('choices', []).append(choice.choice_text)
                else:
                    element['fields'][choice.choice_field] = choice.choice_text
            json_prompts.append(element)
        return json_prompts
