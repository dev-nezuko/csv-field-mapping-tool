import axios from 'axios';
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
export const getCodeAndSuggestions = data => axios.post(`${BASE_URL}/suggest_column_mapping/`, data);
