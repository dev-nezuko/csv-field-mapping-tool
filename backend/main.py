import io
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

MAX_CSV_BYTES = 2 * 1024 * 1024
app = FastAPI(title='CSV mapping preview')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000'],
                   allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['*'])


def _get_mapper():
    load_dotenv(Path(__file__).with_name('.env'))
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key or key in {'replace-me', 'your-key-here'}:
        raise HTTPException(status_code=503, detail='Suggestion provider is not configured. The browser example works without a provider.')
    try:
        from utils.llm_script import ColumnMapper
        mapper = ColumnMapper()
    except ImportError:
        raise HTTPException(status_code=503, detail='Suggestion provider dependencies are unavailable.')
    if mapper is None or not hasattr(mapper, 'llm'):
        raise HTTPException(status_code=503, detail='Suggestion provider could not be initialized.')
    return mapper


async def _read_csv(upload):
    if not (upload.filename or '').lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail='Choose CSV files for both inputs.')
    data = await upload.read(MAX_CSV_BYTES + 1)
    if len(data) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail='Each CSV must be no larger than 2 MiB.')
    try:
        import pandas as pd
        return pd.read_csv(io.StringIO(data.decode('utf-8-sig')))
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=400, detail='The upload must contain a valid UTF-8 CSV table.')


@app.get('/')
async def home():
    return {'message': 'CSV mapping preview backend', 'code_execution_enabled': False}


@app.post('/suggest_column_mapping/')
async def column_suggestions(input_table: UploadFile = File(...),
                             template_table: UploadFile = File(...),
                             suggestion: str = Form(None)):
    mapper = _get_mapper()
    frame = await _read_csv(input_table)
    template = await _read_csv(template_table)
    from utils.templates import main_template, revision_template
    from utils.suggestion_cleaner import clean_suggestion
    try:
        input_info = mapper.get_column_info(frame)
        template_info = mapper.get_column_info(template)
        if suggestion:
            return mapper.suggest_column_mapping(input_info, template_info, revision_template, clean_suggestion(suggestion))
        return mapper.suggest_column_mapping(input_info, template_info, main_template)
    except Exception:
        raise HTTPException(status_code=400, detail='Could not create a preview from those CSV files.')


@app.post('/column_mapper/')
async def column_mapper():
    # Accept no executable input or uploads on the retired execution path.
    raise HTTPException(status_code=503, detail='Code execution is disabled. This application provides suggestions and code previews only.')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)
