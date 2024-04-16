import React, { useState, useEffect, useCallback } from 'react';
import { getCodeAndSuggestions } from './Apis';
import './App.css';

function App() {
  const [source, setSource] = useState(null);
  const [template, setTemplate] = useState(null);
  const [suggestions, setSuggestions] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [example, setExample] = useState(false);
  const loadExample = useCallback(() => {
    setSuggestions('customer_name → full_name\nemail_address → email\norder_total → amount\n\nReview column meanings and missing values before using this mapping.');
    setCode('def map_columns(df):\n    return df.rename(columns={\n        "customer_name": "full_name",\n        "email_address": "email",\n        "order_total": "amount",\n    })');
    setExample(true);
    setError('');
  }, []);
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('demo') === '1') loadExample();
  }, [loadExample]);
  async function generate(event) {
    event.preventDefault();
    if (!source || !template) return;
    setLoading(true); setError('');
    const data = new FormData();
    data.append('input_table', source); data.append('template_table', template);
    if (!example && suggestions) data.append('suggestion', suggestions);
    try {
      const response = await getCodeAndSuggestions(data);
      setSuggestions(String(response.data.suggestion || ''));
      setCode(String(response.data.code || ''));
      setExample(false);
    } catch (failure) {
      const detail = failure.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not generate suggestions. Check the backend and provider configuration.');
    } finally { setLoading(false); }
  }
  return <main className="workspace">
    <header><span className="eyebrow">CSV FIELD MAPPING · PROTOTYPE</span>
      <h1>Different columns.<br />A clearer starting point.</h1>
      <p>Compare a source CSV with a target template, then review a suggested mapping and Python preview.</p>
      <button className="secondary" onClick={loadExample} disabled={loading}>Load example</button>
    </header>
    <aside className="notice">Preview only. Generated Python is never executed by this application. Review it before use in a separately isolated environment.</aside>
    <form onSubmit={generate} className="upload-panel">
      <label htmlFor="source-csv">Source CSV<input id="source-csv" type="file" accept=".csv" onChange={e => setSource(e.target.files[0] || null)} /></label>
      <label htmlFor="template-csv">Template CSV<input id="template-csv" type="file" accept=".csv" onChange={e => setTemplate(e.target.files[0] || null)} /></label>
      <button disabled={!source || !template || loading} type="submit">{loading ? 'Generating…' : 'Generate suggestions'}</button>
      <small>Use synthetic data. Column names and sample values are sent to the configured AI provider. Maximum 2 MiB per CSV.</small>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    {example && <p role="status" className="example">Example preview · illustrative mapping, loaded locally without an AI request.</p>}
    <section className="preview-grid" aria-label="Mapping preview">
      <article><h2><span>01</span> Mapping notes</h2><p>Review the suggested field relationships. Edited notes accompany your next provider request.</p>
        <label className="sr-only" htmlFor="mapping-notes">Mapping notes</label><textarea id="mapping-notes" value={suggestions} onChange={e => setSuggestions(e.target.value)} placeholder="Load the example or generate suggestions to begin." /></article>
      <article><h2><span>02</span> Python preview</h2><p>Editable code for inspection. This is untrusted generated output.</p>
        <label className="sr-only" htmlFor="python-preview">Python preview</label><textarea id="python-preview" className="code" spellCheck="false" value={code} onChange={e => setCode(e.target.value)} placeholder="# Generated code appears here" />
        <button disabled>Execution unavailable</button></article>
    </section>
    <footer>CSV field mapping tool · React + FastAPI · Human review required</footer>
  </main>;
}
export default App;
