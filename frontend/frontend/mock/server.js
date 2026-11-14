// A tiny fake backend (in memory) so you can build every page without the real FastAPI.
// Run: npm run mock   -> http://localhost:4010
// Logins: student@example.com / admin@example.com / reviewer@example.com, password: password123
import express from 'express';
import cors from 'cors';
import { randomUUID as uuid } from 'crypto';

const app = express();
app.use(cors());
app.use(express.json());

const now = () => new Date().toISOString();
const users = [
  { id: 'u-admin', full_name: 'Asha Admin', email: 'admin@example.com', role: 'admin' },
  { id: 'u-rev', full_name: 'Rahul Reviewer', email: 'reviewer@example.com', role: 'reviewer' },
  { id: 'u-stu', full_name: 'Sara Student', email: 'student@example.com', role: 'student' },
];
const scholarships = [
  { id: 's1', title: 'Merit Excellence Award', description: 'For top performers', amount: 50000, deadline: '2026-12-31' },
  { id: 's2', title: 'Need-Based Support Grant', description: 'For families with limited income', amount: 30000, deadline: '2027-01-15' },
  { id: 's3', title: 'STEM Women Scholarship', description: 'Supporting women in STEM', amount: 40000, deadline: '2027-02-01' },
];
const mkApp = (sid, status, student = users[2]) => ({
  id: uuid(), student_id: student.id, student_name: student.full_name,
  scholarship_id: sid, scholarship_title: scholarships.find((s) => s.id === sid).title,
  status, created_at: now(), updated_at: now(),
  profile: { full_name: student.full_name, date_of_birth: '2003-05-14', phone: '9876543210', government_id_number: 'XXXX-XXXX-1234' },
  institution: { institution_name: 'Calcutta University', registration_number: 'REG123', enrollment_number: 'ENR456' },
  address: { address_line: '12 Park Street', city: 'Kolkata', state: 'West Bengal', postal_code: '700016' },
  bank: {},
  documents: status === 'DRAFT' ? [] : ['government_id', 'address_proof', 'cancelled_cheque'].map((t) => ({ id: uuid(), doc_type: t, filename: `${t}.pdf` })),
  history: [{ status, at: now(), remarks: '' }],
});
const applications = [mkApp('s1', 'SUBMITTED'), mkApp('s2', 'VERIFIED'), mkApp('s3', 'CHANGES_REQUESTED'), mkApp('s1', 'APPROVED')];
const notifications = [{ id: uuid(), user_id: 'u-stu', message: 'Welcome to the Scholarship Portal!', read: false, created_at: now() }];

const err = (res, status, message, fields = {}) => res.status(status).json({ message, code: `E${status}`, fields });
const page = (req, list) => {
  const p = Number(req.query.page) || 1, ps = Number(req.query.page_size) || 10;
  return { items: list.slice((p - 1) * ps, p * ps), total: list.length, page: p, page_size: ps };
};
const setStatus = (a, status, remarks = '') => {
  a.status = status; a.updated_at = now(); a.history.push({ status, at: now(), remarks });
  notifications.unshift({ id: uuid(), user_id: a.student_id, message: `Your application for ${a.scholarship_title} is now ${status.replaceAll('_', ' ')}.`, read: false, created_at: now() });
};

// ---- auth ----
const api = express.Router();
api.post('/auth/login', (req, res) => {
  const u = users.find((x) => x.email === req.body.email);
  if (!u || req.body.password !== 'password123') return err(res, 401, 'Wrong email or password');
  res.json({ access_token: `tok-${u.id}`, user: u });
});
api.post('/auth/register', (req, res) => {
  const { full_name, email, password } = req.body;
  const fields = {};
  if (!full_name) fields.full_name = 'Required';
  if (users.some((u) => u.email === email)) fields.email = 'Email already registered';
  if (!password || password.length < 8) fields.password = 'At least 8 characters';
  if (Object.keys(fields).length) return err(res, 422, 'Please fix the highlighted fields', fields);
  users.push({ id: uuid(), full_name, email, role: 'student' });
  res.status(201).json({ ok: true });
});
api.post('/auth/forgot-password', (_req, res) => res.json({ ok: true }));
api.post('/auth/reset-password', (_req, res) => res.json({ ok: true }));
api.get('/scholarships', (req, res) => res.json(page(req, scholarships)));

// ---- everything below needs a token ----
api.use((req, res, next) => {
  const id = (req.headers.authorization || '').replace('Bearer tok-', '');
  req.user = users.find((u) => u.id === id);
  if (!req.user) return err(res, 401, 'Please log in again');
  next();
});
const only = (role) => (req, res, next) => (req.user.role === role ? next() : err(res, 403, 'Not allowed'));
api.get('/auth/me', (req, res) => res.json(req.user));

api.post('/scholarships', only('admin'), (req, res) => {
  const { title, amount, deadline } = req.body; const fields = {};
  if (!title) fields.title = 'Required'; if (!amount) fields.amount = 'Required'; if (!deadline) fields.deadline = 'Required';
  if (Object.keys(fields).length) return err(res, 422, 'Invalid scholarship', fields);
  const s = { id: uuid(), ...req.body }; scholarships.push(s); res.status(201).json(s);
});
api.delete('/scholarships/:id', only('admin'), (req, res) => {
  const i = scholarships.findIndex((s) => s.id === req.params.id); if (i >= 0) scholarships.splice(i, 1); res.json({ ok: true });
});

// ---- student ----
api.get('/applications/mine', only('student'), (req, res) =>
  res.json(page(req, applications.filter((a) => a.student_id === req.user.id && a.status !== 'DRAFT'))));
api.post('/applications', only('student'), (req, res) => {
  let a = applications.find((x) => x.student_id === req.user.id && x.scholarship_id === req.body.scholarship_id);
  if (!a) { a = mkApp(req.body.scholarship_id, 'DRAFT', req.user); a.profile = {}; a.institution = {}; a.address = {}; applications.push(a); }
  res.status(201).json({ id: a.id });
});
api.get('/applications/:id', (req, res) => {
  const a = applications.find((x) => x.id === req.params.id);
  if (!a) return err(res, 404, 'Application not found');
  res.json(a);
});
['profile', 'institution', 'address', 'bank'].forEach((section) =>
  api.put(`/applications/:id/${section}`, only('student'), (req, res) => {
    const a = applications.find((x) => x.id === req.params.id);
    const fields = {};
    Object.entries(req.body).forEach(([k, v]) => { if (!String(v).trim()) fields[k] = 'Required'; });
    if (section === 'bank' && req.body.ifsc && !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(req.body.ifsc)) fields.ifsc = 'Invalid IFSC (e.g. SBIN0001234)';
    if (Object.keys(fields).length) return err(res, 422, 'Please fix the highlighted fields', fields);
    // Bank account numbers come back masked, like the real backend will.
    a[section] = section === 'bank' ? { ...req.body, account_number: '****' + String(req.body.account_number || '').slice(-4) } : req.body;
    res.json(a[section]);
  }));
api.post('/applications/:id/documents', only('student'), express.raw({ type: '*/*', limit: '10mb' }), (req, res) => {
  const a = applications.find((x) => x.id === req.params.id);
  const m = /name="doc_type"\r\n\r\n([^\r]+)/.exec(req.body.toString('latin1')) || [];
  const f = /filename="([^"]+)"/.exec(req.body.toString('latin1')) || [];
  const doc = { id: uuid(), doc_type: m[1] || 'other', filename: f[1] || 'file.pdf' };
  a.documents = a.documents.filter((d) => d.doc_type !== doc.doc_type).concat(doc);
  res.status(201).json(doc);
});
api.post('/applications/:id/submit', only('student'), (req, res) => {
  const a = applications.find((x) => x.id === req.params.id);
  const missing = ['government_id', 'address_proof', 'cancelled_cheque'].filter((t) => !a.documents.some((d) => d.doc_type === t));
  if (missing.length) return err(res, 422, `Missing documents: ${missing.join(', ')}`);
  setStatus(a, 'SUBMITTED'); res.json(a);
});
api.post('/applications/:id/resubmit', only('student'), (req, res) => {
  const a = applications.find((x) => x.id === req.params.id);
  if (a.status !== 'CHANGES_REQUESTED') return err(res, 409, 'Only applications with requested changes can be resubmitted');
  setStatus(a, 'SUBMITTED'); res.json(a);
});
api.post('/applications/:id/withdraw', only('student'), (req, res) => {
  const a = applications.find((x) => x.id === req.params.id); setStatus(a, 'WITHDRAWN'); res.json(a);
});
api.get('/documents/:id/link', (_req, res) => res.json({ url: 'https://placehold.co/600x800?text=Sample+Document' }));

// ---- admin ----
api.get('/admin/applications', only('admin'), (req, res) =>
  res.json(page(req, applications.filter((a) => a.status !== 'DRAFT' && (!req.query.status || a.status === req.query.status)))));
api.post('/admin/applications/:id/verify', only('admin'), (req, res) => {
  const a = applications.find((x) => x.id === req.params.id);
  if (a.status !== 'SUBMITTED') return err(res, 409, 'Illegal status change');
  setStatus(a, req.body.decision, req.body.remarks); res.json(a);
});
api.post('/admin/users', only('admin'), (req, res) => {
  if (users.some((u) => u.email === req.body.email)) return err(res, 422, 'Email already registered', { email: 'Already registered' });
  users.push({ id: uuid(), ...req.body }); res.status(201).json({ ok: true });
});
api.get('/admin/reports/summary', only('admin'), (_req, res) => {
  const by_status = {}; applications.forEach((a) => { by_status[a.status] = (by_status[a.status] || 0) + 1; });
  res.json({ by_status, approval_rate: scholarships.map((s) => ({ scholarship: s.title, round: '2026', rate: Math.random() * 0.8 })) });
});

// ---- reviewer ----
api.get('/reviewer/applications', only('reviewer'), (req, res) =>
  res.json(page(req, applications.filter((a) => a.status === (req.query.status || 'VERIFIED')))));
api.post('/reviewer/applications/:id/review', only('reviewer'), (req, res) => {
  const a = applications.find((x) => x.id === req.params.id);
  if (a.status !== 'VERIFIED') return err(res, 409, 'Illegal status change');
  setStatus(a, req.body.decision, req.body.remarks); res.json(a);
});

// ---- notifications ----
api.get('/notifications', (req, res) => res.json(page(req, notifications.filter((n) => n.user_id === req.user.id))));
api.post('/notifications/:id/read', (req, res) => { const n = notifications.find((x) => x.id === req.params.id); if (n) n.read = true; res.json({ ok: true }); });

app.use('/api', api);
app.listen(4010, () => console.log('Mock API on http://localhost:4010'));
