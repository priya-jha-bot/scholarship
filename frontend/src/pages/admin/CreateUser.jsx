import { useState } from 'react';
import { api } from '../../api';
import { Field, useToast } from '../../components/ui';

export default function CreateUser() {
  const toast = useToast();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'reviewer' });
  const [errors, setErrors] = useState({});
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault(); setErrors({});
    try {
      await api.post('/admin/users', form);
      toast(`${form.role} account created`);
      setForm({ full_name: '', email: '', password: '', role: 'reviewer' });
    } catch (err) { setErrors(err.fields || {}); toast(err.message, 'error'); }
  };

  return (
    <form className="card" style={{ maxWidth: 440 }} onSubmit={submit}>
      <h1>Create reviewer / admin</h1>
      <Field label="Full name" name="full_name" value={form.full_name} onChange={set} error={errors.full_name} required />
      <Field label="Email" name="email" type="email" value={form.email} onChange={set} error={errors.email} required />
      <Field label="Temporary password" name="password" type="password" value={form.password} onChange={set} error={errors.password} minLength={8} required />
      <Field label="Role" name="role" type="select" options={['reviewer', 'admin']} value={form.role} onChange={set} />
      <button className="btn">Create account</button>
    </form>
  );
}
