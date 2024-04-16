import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from utils import prompt_log
from utils.llm_script import ProviderError, get_column_info, split_reply
from utils.suggestion_cleaner import clean_suggestion


class ColumnInfoTests(unittest.TestCase):
    def test_duplicate_columns_are_described_once(self):
        frame = pd.DataFrame({'id': [1, 2], 'copy_of_id': [1, 2], 'name': ['a', 'b']})
        self.assertEqual([column['column_name'] for column in get_column_info(frame)], ['id', 'name'])

    def test_samples_come_from_the_same_rows(self):
        frame = pd.DataFrame({'key': range(50), 'label': [f'row-{n}' for n in range(50)]})
        key, label = get_column_info(frame)
        self.assertEqual(len(key['sample_values']), 5)
        self.assertEqual(label['sample_values'], [f'row-{n}' for n in key['sample_values']])

    def test_header_only_csv_has_no_samples(self):
        info = get_column_info(pd.DataFrame(columns=['a', 'b']))
        self.assertEqual([column['sample_values'] for column in info], [[], []])


class ReplyTests(unittest.TestCase):
    def test_split_on_first_code_marker(self):
        self.assertEqual(split_reply('notes\nCode:\nx = "Code:"'), {'suggestion': 'notes', 'code': 'x = "Code:"'})

    def test_missing_code_marker_raises(self):
        with self.assertRaises(ProviderError):
            split_reply('only notes')

    def test_clean_suggestion_drops_rationale_and_expands_newlines(self):
        self.assertEqual(clean_suggestion('a -> b\\nRationale: same'), 'a -> b\n')
        self.assertEqual(clean_suggestion('a -> b'), 'a -> b')


class PromptLogTests(unittest.TestCase):
    def test_empty_path_disables_logging(self):
        with patch.dict(os.environ, {'PROMPT_LOG_PATH': ''}):
            self.assertIsNone(prompt_log.log_path())
            prompt_log.record_prompt('p', 'r')

    def test_default_path_does_not_depend_on_working_directory(self):
        with patch.dict(os.environ, {}, clear=True), tempfile.TemporaryDirectory() as directory:
            previous = os.getcwd()
            os.chdir(directory)
            try:
                self.assertEqual(prompt_log.log_path(), Path(prompt_log.__file__).resolve().parent.parent / 'llmdatabase.db')
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
