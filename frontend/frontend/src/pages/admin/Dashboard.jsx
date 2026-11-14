import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, qs } from '../../api';
import { Loading, ErrorBox, DataTable, StatusBadge, Pager } from '../../components/ui';

const FILTERS = ['SUBMITTED', 'VERIFIED', 'REJECTED_BY_ADMIN', 'CHANGES_REQUESTED', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'DISBURSED'];

export default function AdminDashboard() {
  const [status, setStatus] = useState('SUBMITTED');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const pageSize = 10;

  useEffect(() => {
    setData(null);
    api.get(`/admin/applications${qs({ status, page, page_size: pageSize })}`).then(setData).catch(setError);
  }, [status, page]);

  return (
    <>
      <h1>Applications</h1>
      <div className="row" style={{ marginBottom: 12 }}>
        <label>Status:&nbsp;
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            {FILTERS.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
      </div>
      <ErrorBox error={error} />
      {!data && !error ? <Loading /> : data && (
        <div className="card">
          <DataTable
            rows={data.items}
            empty="No applications with this status."
            columns={[
              { header: 'Student', render: (a) => a.student_name },
              { header: 'Scholarship', render: (a) => a.scholarship_title },
              { header: 'Status', render: (a) => <StatusBadge status={a.status} /> },
              { header: '', render: (a) => (a.status === 'SUBMITTED' ? <Link to={`/admin/verify/${a.id}`}>Verify</Link> : <Link to={`/admin/verify/${a.id}`}>View</Link>) },
            ]}
          />
          <Pager page={data.page} pageSize={data.page_size} total={data.total} onPage={setPage} />
        </div>
      )}
    </>
  );
}
