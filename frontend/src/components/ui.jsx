// FE-3: shared building blocks used by every page.
import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { api } from '../api';

/* ---------- Toasts ---------- */
const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = useCallback((message, type = 'success') => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts">
        {toasts.map((t) => <div key={t.id} className={`toast ${t.type}`}>{t.message}</div>)}
      </div>
    </ToastCtx.Provider>
  );
}

/* ---------- Loading / error ---------- */
export const Loading = () => <p className="muted">Loading…</p>;
export const ErrorBox = ({ error }) =>
  error ? <div className="card" style={{ color: 'var(--bad)' }}>{error.message || String(error)}</div> : null;

/* ---------- Form field (shows field-level errors from the backend) ---------- */
export function Field({ label, name, value, onChange, error, type = 'text', options, ...rest }) {
  const common = { id: name, name, value: value ?? '', onChange: (e) => onChange(name, e.target.value), className: error ? 'invalid' : '', ...rest };
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      {type === 'select' ? (
        <select {...common}>
          <option value="">Select…</option>
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : type === 'textarea' ? (
        <textarea rows={3} {...common} />
      ) : (
        <input type={type} {...common} />
      )}
      {error && <span className="error">{error}</span>}
    </div>
  );
}

/* ---------- Status badge ---------- */
export const StatusBadge = ({ status }) => (
  <span className={`badge ${status}`}>{(status || '').replaceAll('_', ' ')}</span>
);

/* ---------- Table ---------- */
// columns: [{ header: 'Name', render: (row) => ... }]
export function DataTable({ columns, rows, empty = 'Nothing here yet.' }) {
  if (!rows?.length) return <p className="muted">{empty}</p>;
  return (
    <table>
      <thead><tr>{columns.map((c) => <th key={c.header}>{c.header}</th>)}</tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.id || i}>{columns.map((c) => <td key={c.header}>{c.render(r)}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}

/* ---------- Pagination ---------- */
export function Pager({ page, pageSize, total, onPage }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="row" style={{ marginTop: 12 }}>
      <button className="btn secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>Prev</button>
      <span className="muted">Page {page} of {pages}</span>
      <button className="btn secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
    </div>
  );
}

/* ---------- Modal ---------- */
export function Modal({ title, children, onClose }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}

/* ---------- File upload ---------- */
// Uploads immediately to POST /applications/{id}/documents with doc_type.
export function FileUpload({ label, docType, applicationId, existing, onUploaded }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const input = useRef();
  const toast = useToast();

  const pick = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { setError('File must be under 5 MB'); return; }
    setBusy(true); setError('');
    try {
      const doc = await api.upload(`/applications/${applicationId}/documents`, file, docType);
      toast(`${label} uploaded`);
      onUploaded?.(doc);
    } catch (err) {
      setError(err.fields?.file || err.message);
    } finally {
      setBusy(false);
      input.current.value = '';
    }
  };

  return (
    <div className="field">
      <label>{label}</label>
      <input ref={input} type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={pick} disabled={busy} />
      {busy && <span className="muted">Uploading…</span>}
      {existing && !busy && <span className="muted">✔ Uploaded: {existing.filename}</span>}
      {error && <span className="error">{error}</span>}
    </div>
  );
}
