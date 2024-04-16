import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import main

spec = importlib.util.spec_from_file_location('retired_runner', Path(__file__).parent / 'utils/code_executor.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ExecutionBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_runner_cannot_execute_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'must-not-exist'
            payload = f'open({str(target)!r}, "w").write("executed")'
            with self.assertRaises(runner.CodeExecutionDisabled):
                runner.code_runner(payload, object())
            self.assertFalse(target.exists())

    async def test_http_execution_path_is_unavailable_for_any_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'must-not-exist'
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
                response = await client.post('/column_mapper/', data={'code': f'open({str(target)!r}, "w").write("executed")'})
            self.assertEqual(response.status_code, 503)
            self.assertFalse(target.exists())

    async def test_backend_starts_without_provider_credentials(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
                response = await client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['code_execution_enabled'])

    async def test_missing_provider_is_an_explicit_service_error(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
                response = await client.post('/suggest_column_mapping/', files={
                    'input_table': ('source.csv', b'a\n1\n', 'text/csv'),
                    'template_table': ('target.csv', b'b\n1\n', 'text/csv')})
            self.assertEqual(response.status_code, 503)


if __name__ == '__main__':
    unittest.main()
