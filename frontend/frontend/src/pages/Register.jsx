import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { Field, useToast } from '../components/ui';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ full_name: '', email: '', password: '' });
  const [errors, setErrors] = useState({});
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setErrors({});
    try {
      await register(form);
      toast('Account created!');
      navigate('/student');
    } catch (err) {
      setErrors(err.fields || {});
      toast(err.message, 'error');
    }
  };

  return (
    <form className="card" style={{ maxWidth: 400, margin: '0 auto' }} onSubmit={submit}>
      <h1>Student registration</h1>
      <Field label="Full name" name="full_name" value={form.full_name} onChange={set} error={errors.full_name} required />
      <Field label="Email" name="email" type="email" value={form.email} onChange={set} error={errors.email} required />
      <Field label="Password (min 8 characters)" name="password" type="password" value={form.password} onChange={set} error={errors.password} minLength={8} required />
      <button className="btn">Create account</button>
    </form>
  );
}
