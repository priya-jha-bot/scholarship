import { useEffect, useState, useCallback } from 'react';
import { api } from '../../api';
import { Loading, ErrorBox, DataTable, Field, Modal, useToast } from '../../components/ui';

const EMPTY = { title: '', description: '', amount: '', deadline: '' };

export default function Scholarships() {
  const toast = useToast();
  const [list, setList] = useState(null);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(() => api.get('/scholarships').then((r) => setList(r.items)).catch(setError), []);
  useEffect(() => { load(); }, [load]);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const create = async (e) => {
    e.preventDefault(); setErrors({});
    try {
      await api.post('/scholarships', { ...form, amount: Number(form.amount) });
      toast('Scholarship created'); setShowForm(false); setForm(EMPTY); load();
    } catch (err) { setErrors(err.fields || {}); toast(err.message, 'error'); }
  };
  const remove = async (id) => {
    if (!window.confirm('Delete this scholarship?')) return;
    try { await api.del(`/scholarships/${id}`); toast('Deleted'); load(); }
    catch (err) { toast(err.message, 'error'); }
  };

  if (error) return <ErrorBox error={error} />;
  if (!list) return <Loading />;
  return (
    <>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>Scholarships</h1>
        <button className="btn" onClick={() => setShowForm(true)}>+ New scholarship</button>
      </div>
      <div className="card">
        <DataTable rows={list} columns={[
          { header: 'Title', render: (s) => s.title },
          { header: 'Amount', render: (s) => `₹${s.amount}` },
          { header: 'Deadline', render: (s) => s.deadline },
          { header: '', render: (s) => <button className="btn danger" onClick={() => remove(s.id)}>Delete</button> },
        ]} />
      </div>
      {showForm && (
        <Modal title="New scholarship" onClose={() => setShowForm(false)}>
          <form onSubmit={create}>
            <Field label="Title" name="title" value={form.title} onChange={set} error={errors.title} required />
            <Field label="Description" name="description" type="textarea" value={form.description} onChange={set} error={errors.description} />
            <Field label="Amount (₹)" name="amount" type="number" value={form.amount} onChange={set} error={errors.amount} required />
            <Field label="Deadline" name="deadline" type="date" value={form.deadline} onChange={set} error={errors.deadline} required />
            <button className="btn">Create</button>
          </form>
        </Modal>
      )}
    </>
  );
}
