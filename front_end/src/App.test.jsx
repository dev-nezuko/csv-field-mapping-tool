import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import { getCodeAndSuggestions } from './Apis';
vi.mock('./Apis', () => ({ getCodeAndSuggestions: vi.fn() }));
beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState(null, '', '/');
});
function chooseBothFiles() {
  for (const label of ['Source CSV', 'Template CSV']) {
    fireEvent.change(screen.getByLabelText(label), { target: { files: [new File(['a\n1'], `${label.split(' ')[0].toLowerCase()}.csv`, { type: 'text/csv' })] } });
  }
}
function sentFields() {
  return Object.fromEntries(getCodeAndSuggestions.mock.calls.at(-1)[0].entries());
}
test('execution is unavailable and generation requires both CSV files', () => {
  render(<App />);
  expect(screen.getByRole('button', { name: 'Execution unavailable' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Generate suggestions' })).toBeDisabled();
  expect(screen.getByText(/Choose a source and a template CSV/)).toBeInTheDocument();
  chooseBothFiles();
  expect(screen.queryByText(/Choose a source and a template CSV/)).not.toBeInTheDocument();
});
test('example loads locally and clearly labels illustrative output', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'Load example' }));
  expect(screen.getByRole('status')).toHaveTextContent('illustrative mapping');
  expect(screen.getByLabelText('Python preview').value).toContain('def map_columns');
  expect(getCodeAndSuggestions).not.toHaveBeenCalled();
});
test('demo query parameter opens the example', () => {
  window.history.replaceState(null, '', '/?demo=1');
  render(<App />);
  expect(screen.getByLabelText('Mapping notes').value).toContain('customer_name');
});
test('provider failures are visible and the form becomes usable again', async () => {
  getCodeAndSuggestions.mockRejectedValue({ response: { data: { detail: 'Configure a provider key.' } } });
  render(<App />);
  chooseBothFiles();
  fireEvent.click(screen.getByRole('button', { name: 'Generate suggestions' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Configure a provider key.');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate suggestions' })).toBeEnabled());
});
test('a network failure without a detail gets a generic message', async () => {
  getCodeAndSuggestions.mockRejectedValue(new Error('Network Error'));
  render(<App />);
  chooseBothFiles();
  fireEvent.click(screen.getByRole('button', { name: 'Generate suggestions' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Check the backend and provider configuration');
});
test('shows a busy state, then fills both panels from the provider reply', async () => {
  let reply;
  getCodeAndSuggestions.mockReturnValue(new Promise(resolve => { reply = resolve; }));
  render(<App />);
  chooseBothFiles();
  fireEvent.click(screen.getByRole('button', { name: 'Generate suggestions' }));
  expect(screen.getByRole('button', { name: 'Generating…' })).toBeDisabled();
  reply({ data: { suggestion: 'name -> full_name', code: 'def map_columns(df):\n    return df' } });
  await waitFor(() => expect(screen.getByLabelText('Mapping notes')).toHaveValue('name -> full_name'));
  expect(screen.getByLabelText('Python preview').value).toContain('def map_columns');
  expect(sentFields()).not.toHaveProperty('suggestion');
});
test('edited provider notes accompany the next request, example notes do not', async () => {
  getCodeAndSuggestions.mockResolvedValue({ data: { suggestion: 'a -> b', code: 'pass' } });
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'Load example' }));
  chooseBothFiles();
  fireEvent.click(screen.getByRole('button', { name: 'Generate suggestions' }));
  await waitFor(() => expect(screen.getByLabelText('Mapping notes')).toHaveValue('a -> b'));
  expect(sentFields()).not.toHaveProperty('suggestion');
  fireEvent.change(screen.getByLabelText('Mapping notes'), { target: { value: 'a -> c' } });
  fireEvent.click(screen.getByRole('button', { name: 'Generate suggestions' }));
  await waitFor(() => expect(getCodeAndSuggestions).toHaveBeenCalledTimes(2));
  expect(sentFields().suggestion).toBe('a -> c');
});
