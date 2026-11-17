import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth, HOME_BY_ROLE } from '../AuthContext';
import { Field, useToast } from '../components/ui';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErrors({});
    try {
      const me = await login(form.email, form.password);
      navigate(HOME_BY_ROLE[me.role]);
    } catch (err) {
      setErrors(err.fields || {});
      toast(err.message, 'error');
    } finally { setBusy(false); }
  };

  return (
    <form className="card" style={{ maxWidth: 400, margin: '0 auto' }} onSubmit={submit}>
      <h1>Log in</h1>
      <Field label="Email" name="email" type="email" value={form.email} onChange={set} error={errors.email} required />
      <Field label="Password" name="password" type="password" value={form.password} onChange={set} error={errors.password} required />
      <button className="btn" disabled={busy}>{busy ? 'Logging in…' : 'Log in'}</button>
      <p className="muted"><Link to="/forgot-password">Forgot password?</Link> · <Link to="/register">Create account</Link></p>
    </form>
  );
}
