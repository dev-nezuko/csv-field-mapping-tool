import io
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from utils.llm_script import ColumnMapper, ProviderError, get_column_info
from utils.suggestion_cleaner import clean_suggestion
from utils.templates import main_template, revision_template

load_dotenv(Path(__file__).with_name('.env'))

MAX_CSV_BYTES = 2 * 1024 * 1024
PLACEHOLDER_KEYS = {'', 'replace-me', 'your-key-here'}
CORS_ORIGINS = [origin.strip() for origin in
                os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
                if origin.strip()]

app = FastAPI(title='CSV mapping preview')
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['*'])


def get_mapper():
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if key in PLACEHOLDER_KEYS:
        raise HTTPException(status_code=503, detail='Suggestion provider is not configured. The browser example works without a provider.')
    return ColumnMapper(api_key=key)


async def read_csv(upload):
    if not (upload.filename or '').lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail='Choose CSV files for both inputs.')
    data = await upload.read(MAX_CSV_BYTES + 1)
    if len(data) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail='Each CSV must be no larger than 2 MiB.')
    try:
        return pd.read_csv(io.StringIO(data.decode('utf-8-sig')))
    except (UnicodeDecodeError, ValueError):
        # pandas parser and empty-file errors are ValueError subclasses.
        raise HTTPException(status_code=400, detail='The upload must contain a valid UTF-8 CSV table.')


@app.get('/')
async def home():
    return {'message': 'CSV mapping preview backend', 'code_execution_enabled': False}


@app.post('/suggest_column_mapping/')
async def column_suggestions(input_table: UploadFile = File(...),
                             template_table: UploadFile = File(...),
                             suggestion: str | None = Form(None)):
    mapper = get_mapper()
    input_info = get_column_info(await read_csv(input_table))
    template_info = get_column_info(await read_csv(template_table))
    try:
        if suggestion:
            return mapper.suggest_column_mapping(input_info, template_info, revision_template, clean_suggestion(suggestion))
        return mapper.suggest_column_mapping(input_info, template_info, main_template)
    except ProviderError as error:
        raise HTTPException(status_code=502, detail=f'{error} Try again or check the provider configuration.')


@app.post('/column_mapper/')
async def column_mapper():
    # Accept no executable input or uploads on the retired execution path.
    raise HTTPException(status_code=503, detail='Code execution is disabled. This application provides suggestions and code previews only.')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)
