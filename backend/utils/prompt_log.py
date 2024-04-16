"""Keep a local record of each prompt and reply so mappings can be reviewed later.

Set PROMPT_LOG_PATH to change the file, or to an empty value to switch it off.
"""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / 'llmdatabase.db'


def log_path():
    value = os.getenv('PROMPT_LOG_PATH')
    if value is None:
        return DEFAULT_PATH
    return Path(value) if value.strip() else None


def record_prompt(prompt, response):
    path = log_path()
    if path is None:
        return
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute('CREATE TABLE IF NOT EXISTS llm_data ('
                           'id INTEGER PRIMARY KEY, prompt TEXT NOT NULL, response TEXT NOT NULL)')
        connection.execute('INSERT INTO llm_data (prompt, response) VALUES (?, ?)', (prompt, response))
