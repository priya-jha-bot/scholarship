// FE-2: one place that talks to the backend. Every page uses this, never fetch() directly.
const BASE = import.meta.env.VITE_API_BASE || '/api';

export const getToken = () => localStorage.getItem('token');
export const setToken = (t) => (t ? localStorage.setItem('token', t) : localStorage.removeItem('token'));

// Matches the contract's error shape: { message, code, fields }
export class ApiError extends Error {
  constructor(status, body) {
    super(body?.message || 'Something went wrong');
    this.status = status;
    this.code = body?.code;
    this.fields = body?.fields || {};
  }
}

async function request(method, path, body, isForm = false) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body && !isForm) headers['Content-Type'] = 'application/json';

  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
    });
  } catch {
    throw new ApiError(0, { message: 'Cannot reach the server. Is it running?' });
  }

  let data = null;
  try { data = await res.json(); } catch { /* empty body is fine */ }

  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/login')) {
      setToken(null);
      window.dispatchEvent(new Event('auth:expired'));
    }
    throw new ApiError(res.status, data);
  }
  return data;
}

export const api = {
  get: (p) => request('GET', p),
  post: (p, b) => request('POST', p, b ?? {}),
  put: (p, b) => request('PUT', p, b ?? {}),
  del: (p) => request('DELETE', p),
  upload: (p, file, docType) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('doc_type', docType);
    return request('POST', p, fd, true);
  },
};

export const qs = (obj) => {
  const p = new URLSearchParams();
  Object.entries(obj).forEach(([k, v]) => v !== '' && v != null && p.append(k, v));
  const s = p.toString();
  return s ? `?${s}` : '';
};
