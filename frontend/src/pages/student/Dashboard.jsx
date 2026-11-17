import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api';
import { Loading, ErrorBox, DataTable, StatusBadge } from '../../components/ui';

export default function StudentDashboard() {
  const [apps, setApps] = useState(null);
  const [scholarships, setScholarships] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.get('/applications/mine'), api.get('/scholarships')])
      .then(([a, s]) => { setApps(a.items); setScholarships(s.items); })
      .catch(setError);
  }, []);

  if (error) return <ErrorBox error={error} />;
  if (!apps) return <Loading />;

  return (
    <>
      <h1>My dashboard</h1>
      <div className="card">
        <h2>My applications</h2>
        <DataTable
          rows={apps}
          empty="You have not applied yet. Pick a scholarship below."
          columns={[
            { header: 'Scholarship', render: (a) => a.scholarship_title },
            { header: 'Status', render: (a) => <StatusBadge status={a.status} /> },
            { header: 'Updated', render: (a) => new Date(a.updated_at).toLocaleDateString() },
            { header: '', render: (a) => <Link to={`/student/applications/${a.id}`}>View</Link> },
          ]}
        />
      </div>
      <div className="card">
        <h2>Open scholarships</h2>
        <DataTable
          rows={scholarships}
          columns={[
            { header: 'Title', render: (s) => s.title },
            { header: 'Amount', render: (s) => `₹${s.amount}` },
            { header: 'Deadline', render: (s) => s.deadline },
            { header: '', render: (s) => <Link className="btn" to={`/student/apply/${s.id}`}>Apply</Link> },
          ]}
        />
      </div>
    </>
  );
}
