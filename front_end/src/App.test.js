import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import { getCodeAndSuggestions } from './Apis';
jest.mock('./Apis', () => ({ getCodeAndSuggestions: jest.fn() }));
beforeEach(() => jest.clearAllMocks());
test('execution is unavailable and generation requires both CSV files', () => {
  render(<App />);
  expect(screen.getByRole('button', { name: 'Execution unavailable' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Generate suggestions' })).toBeDisabled();
});
test('example loads locally and clearly labels illustrative output', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'Load example' }));
  expect(screen.getByRole('status')).toHaveTextContent('illustrative mapping');
  expect(screen.getByLabelText('Python preview').value).toContain('def map_columns');
  expect(getCodeAndSuggestions).not.toHaveBeenCalled();
});
test('provider failures are visible and the form becomes usable again', async () => {
  getCodeAndSuggestions.mockRejectedValue({ response: { data: { detail: 'Configure a provider key.' } } });
  render(<App />);
  for (const label of ['Source CSV', 'Template CSV']) {
    fireEvent.change(screen.getByLabelText(label), { target: { files: [new File(['a\n1'], 'sample.csv', {type: 'text/csv'})] } });
  }
  fireEvent.click(screen.getByRole('button', { name: 'Generate suggestions' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Configure a provider key.');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Generate suggestions' })).toBeEnabled());
});
