import { useEffect, useState } from 'react';
import { api } from '../../api';
import { Loading, ErrorBox, DataTable } from '../../components/ui';

export default function Reports() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => { api.get('/admin/reports/summary').then(setData).catch(setError); }, []);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;
  const max = Math.max(1, ...Object.values(data.by_status));
  return (
    <>
      <h1>Reports</h1>
      <div className="card">
        <h2>Applications by status</h2>
        {Object.entries(data.by_status).map(([s, n]) => (
          <div key={s} style={{ marginBottom: 8 }}>
            <div className="row" style={{ justifyContent: 'space-between' }}><span>{s.replaceAll('_', ' ')}</span><strong>{n}</strong></div>
            <div className="bar"><div style={{ width: `${(n / max) * 100}%` }} /></div>
          </div>
        ))}
      </div>
      <div className="card">
        <h2>Approval rate per scholarship</h2>
        <DataTable rows={data.approval_rate} columns={[
          { header: 'Scholarship', render: (r) => r.scholarship },
          { header: 'Round', render: (r) => r.round },
          { header: 'Approval rate', render: (r) => `${Math.round(r.rate * 100)}%` },
        ]} />
      </div>
    </>
  );
}
