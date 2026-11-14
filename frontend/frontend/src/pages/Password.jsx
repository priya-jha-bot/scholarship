import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Field, useToast } from '../components/ui';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const toast = useToast();
  const submit = async (e) => {
    e.preventDefault();
    try { await api.post('/auth/forgot-password', { email }); setSent(true); }
    catch (err) { toast(err.message, 'error'); }
  };
  return (
    <form className="card" style={{ maxWidth: 400, margin: '0 auto' }} onSubmit={submit}>
      <h1>Forgot password</h1>
      {sent ? <p>If that email exists, a reset link has been sent.</p> : (
        <>
          <Field label="Email" name="email" type="email" value={email} onChange={(_, v) => setEmail(v)} required />
          <button className="btn">Send reset link</button>
        </>
      )}
    </form>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [password, setPassword] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/auth/reset-password', { token: params.get('token'), password });
      toast('Password updated. Please log in.');
      navigate('/login');
    } catch (err) { toast(err.message, 'error'); }
  };
  return (
    <form className="card" style={{ maxWidth: 400, margin: '0 auto' }} onSubmit={submit}>
      <h1>Reset password</h1>
      <Field label="New password" name="password" type="password" value={password} onChange={(_, v) => setPassword(v)} minLength={8} required />
      <button className="btn">Update password</button>
    </form>
  );
}
