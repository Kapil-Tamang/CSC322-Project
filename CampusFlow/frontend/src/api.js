const API_BASE = 'http://127.0.0.1:8000';
const TOKEN_KEY = 'campusflow_final_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export async function api(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token && options.auth !== false) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    throw new Error(formatError(data) || `Request failed: ${response.status}`);
  }
  return data;
}

function formatError(data) {
  if (!data) return null;
  const d = data.detail ?? data.message;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d.map(item => {
      if (typeof item === 'string') return item;
      const field = Array.isArray(item?.loc) ? item.loc.filter(p => p !== 'body').join('.') : '';
      const msg = item?.msg || 'invalid value';
      return field ? `${field}: ${msg}` : msg;
    }).join('; ');
  }
  if (d && typeof d === 'object') return d.msg || JSON.stringify(d);
  return null;
}
