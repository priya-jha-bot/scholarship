import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { Loading, ErrorBox } from '../components/ui';

export default function Home() {
  const [list, setList] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => { api.get('/scholarships').then((r) => setList(r.items)).catch(setError); }, []);
  return (
    <>
      <div className="card">
        <h1>Find and apply for scholarships</h1>
        <p>Create an account, pick a scholarship, and track your application in one place.</p>
        <Link className="btn" to="/register">Get started</Link>
      </div>
      <h2>Open scholarships</h2>
      <ErrorBox error={error} />
      {!list && !error ? <Loading /> : list?.map((s) => (
        <div className="card" key={s.id}>
          <strong>{s.title}</strong> — ₹{s.amount}
          <p className="muted">{s.description} · Deadline: {s.deadline}</p>
        </div>
      ))}
    </>
  );
}
