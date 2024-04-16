"""Ask an OpenAI model for mapping notes and a Python preview.

The reply is returned as text for a person to read. Nothing here, or anywhere
else in the backend, executes the generated code.
"""
import os

import openai

from .prompt_log import record_prompt

DEFAULT_MODEL = 'gpt-4o-mini'
SAMPLE_ROWS = 5


class ProviderError(RuntimeError):
    """The provider call failed or its reply did not follow the requested format."""


def get_column_info(df):
    """Describe each distinct column with its dtype and values from the same sampled rows."""
    df = df.loc[:, ~df.T.duplicated(keep='first')]
    rows = df.sample(n=min(SAMPLE_ROWS, len(df)), random_state=0)
    return [{'column_name': str(column),
             'data_type': str(df[column].dtype),
             'sample_values': rows[column].tolist()}
            for column in df.columns]


def split_reply(reply):
    notes, marker, code = reply.partition('Code:')
    if not marker:
        raise ProviderError('The provider reply did not contain a "Code:" section.')
    return {'suggestion': notes.strip(), 'code': code.strip()}


class ColumnMapper:
    def __init__(self, api_key, client=None, model=None):
        # The SDK only opens a connection when a request is made.
        self.client = client or openai.OpenAI(api_key=api_key, timeout=60, max_retries=1)
        self.model = model or os.getenv('OPENAI_MODEL') or DEFAULT_MODEL

    def suggest_column_mapping(self, info_input, info_template, template, suggestion=None):
        values = {'info_input': info_input, 'info_template': info_template}
        if suggestion:
            values['suggestion'] = suggestion
        prompt = template.format(**values)
        try:
            completion = self.client.chat.completions.create(
                model=self.model, temperature=0, max_tokens=1500,
                messages=[{'role': 'user', 'content': prompt}])
        except openai.OpenAIError as error:
            raise ProviderError('The suggestion provider request failed.') from error
        reply = completion.choices[0].message.content or ''
        record_prompt(prompt, reply)
        return split_reply(reply)
