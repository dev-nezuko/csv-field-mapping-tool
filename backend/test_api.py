"""API behaviour with a fake provider. No test makes a network request or uses a real key."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import openai

import main
from utils import llm_script

FAKE_KEY = 'sk-test-not-a-real-key'
SOURCE = ('source.csv', b'customer_name,email_address,order_total\nAda,ada@example.test,12.5\n', 'text/csv')
TARGET = ('target.csv', b'full_name,email,amount\nGrace,grace@example.test,7\n', 'text/csv')
REPLY = 'Suggestions:\ncustomer_name -> full_name\nRationale:\nSame meaning\nCode:\ndef map_columns(df):\n    return df'


class FakeCompletions:
    def __init__(self, reply=REPLY, error=None):
        self.reply, self.error, self.prompts = reply, error, []

    def create(self, **request):
        self.prompts.append(request['messages'][0]['content'])
        if self.error:
            raise self.error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))])


class SuggestionApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.log = Path(self.directory.name) / 'prompts.db'
        env = patch.dict(os.environ, {'OPENAI_API_KEY': FAKE_KEY, 'PROMPT_LOG_PATH': str(self.log)})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(self.directory.cleanup)
        self.completions = FakeCompletions()
        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=self.completions))
        mapper = patch.object(main, 'ColumnMapper', lambda api_key: llm_script.ColumnMapper(api_key, client=fake_client))
        mapper.start()
        self.addCleanup(mapper.stop)

    async def post(self, files=None, data=None):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
            files = files or {'input_table': SOURCE, 'template_table': TARGET}
            return await client.post('/suggest_column_mapping/', files=files, data=data)

    async def test_returns_notes_and_code_as_text(self):
        response = await self.post()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['suggestion'].startswith('Suggestions:'))
        self.assertTrue(body['code'].startswith('def map_columns'))
        self.assertIn('customer_name', self.completions.prompts[0])
        self.assertIn('full_name', self.completions.prompts[0])

    async def test_generated_code_is_returned_not_executed(self):
        marker = Path(self.directory.name) / 'must-not-exist'
        self.completions.reply = f'notes\nCode:\nopen({str(marker)!r}, "w").write("executed")'
        response = await self.post()
        self.assertEqual(response.status_code, 200)
        self.assertIn('must-not-exist', response.json()['code'])
        self.assertFalse(marker.exists())

    async def test_revision_request_uses_edited_notes_without_rationale(self):
        response = await self.post(data={'suggestion': 'customer_name -> full_name\\nRationale: old reasoning'})
        self.assertEqual(response.status_code, 200)
        prompt = self.completions.prompts[0]
        self.assertIn('customer_name -> full_name', prompt)
        self.assertNotIn('old reasoning', prompt)

    async def test_prompt_and_reply_are_logged_to_the_configured_file(self):
        await self.post()
        with sqlite3.connect(self.log) as connection:
            rows = connection.execute('SELECT prompt, response FROM llm_data').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], REPLY)

    async def test_reply_without_code_section_is_a_gateway_error(self):
        self.completions.reply = 'I could not map these columns.'
        response = await self.post()
        self.assertEqual(response.status_code, 502)
        self.assertIn('Code:', response.json()['detail'])

    async def test_provider_failure_is_a_gateway_error(self):
        self.completions.error = openai.APIConnectionError(request=httpx.Request('POST', 'https://provider.invalid'))
        response = await self.post()
        self.assertEqual(response.status_code, 502)
        self.assertFalse(self.log.exists())

    async def test_rejects_non_csv_upload(self):
        response = await self.post(files={'input_table': ('notes.txt', b'a\n1\n', 'text/plain'), 'template_table': TARGET})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.completions.prompts, [])

    async def test_rejects_upload_over_two_mebibytes(self):
        big = b'a\n' + b'1\n' * (main.MAX_CSV_BYTES // 2 + 1)
        response = await self.post(files={'input_table': ('big.csv', big, 'text/csv'), 'template_table': TARGET})
        self.assertEqual(response.status_code, 413)

    async def test_rejects_non_utf8_and_empty_csv(self):
        for content in (b'\xff\xfe\x00bad', b''):
            with self.subTest(content=content):
                response = await self.post(files={'input_table': ('bad.csv', content, 'text/csv'), 'template_table': TARGET})
                self.assertEqual(response.status_code, 400)

    async def test_placeholder_key_counts_as_unconfigured(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'replace-me'}):
            response = await self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.completions.prompts, [])


if __name__ == '__main__':
    unittest.main()
