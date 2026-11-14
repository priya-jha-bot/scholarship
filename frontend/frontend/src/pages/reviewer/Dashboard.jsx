import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, qs } from '../../api';
import { Loading, ErrorBox, DataTable, StatusBadge, Pager } from '../../components/ui';

// "Pending" = verified by admin, waiting for review. The others are history.
const VIEWS = { Pending: 'VERIFIED', Approved: 'APPROVED', Rejected: 'REJECTED', 'Changes requested': 'CHANGES_REQUESTED' };

export default function ReviewerDashboard() {
  const [view, setView] = useState('Pending');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    api.get(`/reviewer/applications${qs({ status: VIEWS[view], page, page_size: 10 })}`).then(setData).catch(setError);
  }, [view, page]);

  return (
    <>
      <h1>Reviews</h1>
      <div className="row" style={{ marginBottom: 12 }}>
        {Object.keys(VIEWS).map((v) => (
          <button key={v} className={`btn ${v === view ? '' : 'secondary'}`} onClick={() => { setView(v); setPage(1); }}>{v}</button>
        ))}
      </div>
      <ErrorBox error={error} />
      {!data && !error ? <Loading /> : data && (
        <div className="card">
          <DataTable rows={data.items} empty="Nothing in this list." columns={[
            { header: 'Student', render: (a) => a.student_name },
            { header: 'Scholarship', render: (a) => a.scholarship_title },
            { header: 'Status', render: (a) => <StatusBadge status={a.status} /> },
            { header: '', render: (a) => <Link to={`/reviewer/review/${a.id}`}>{a.status === 'VERIFIED' ? 'Review' : 'View'}</Link> },
          ]} />
          <Pager page={data.page} pageSize={data.page_size} total={data.total} onPage={setPage} />
        </div>
      )}
    </>
  );
}
