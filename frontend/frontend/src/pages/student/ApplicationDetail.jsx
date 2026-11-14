import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../../api';
import { Loading, ErrorBox, StatusBadge, Modal, useToast } from '../../components/ui';

const CAN_WITHDRAW = ['SUBMITTED', 'VERIFIED', 'CHANGES_REQUESTED'];

export default function ApplicationDetail() {
  const { id } = useParams();
  const toast = useToast();
  const [app, setApp] = useState(null);
  const [error, setError] = useState(null);
  const [confirm, setConfirm] = useState(false);

  const load = useCallback(() => api.get(`/applications/${id}`).then(setApp).catch(setError), [id]);
  useEffect(() => { load(); }, [load]);

  const act = async (action, msg) => {
    try { await api.post(`/applications/${id}/${action}`); toast(msg); setConfirm(false); load(); }
    catch (err) { toast(err.message, 'error'); }
  };

  if (error) return <ErrorBox error={error} />;
  if (!app) return <Loading />;

  return (
    <>
      <h1>{app.scholarship_title}</h1>
      <div className="card">
        <div className="row">
          <StatusBadge status={app.status} />
          {app.status === 'CHANGES_REQUESTED' && (
            <>
              <Link className="btn" to={`/student/apply/${app.scholarship_id}`}>Edit &amp; resubmit</Link>
              <button className="btn secondary" onClick={() => act('resubmit', 'Resubmitted')}>Resubmit as is</button>
            </>
          )}
          {CAN_WITHDRAW.includes(app.status) && <button className="btn danger" onClick={() => setConfirm(true)}>Withdraw</button>}
        </div>
      </div>

      <div className="split">
        <div className="card">
          <h2>Status timeline</h2>
          <ul className="timeline">
            {(app.history || []).map((h, i) => (
              <li key={i}>
                <StatusBadge status={h.status} />
                <div className="muted">{new Date(h.at).toLocaleString()}{h.remarks ? ` — ${h.remarks}` : ''}</div>
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2>Documents</h2>
          {(app.documents || []).map((d) => <div key={d.id}>{d.doc_type.replaceAll('_', ' ')} — <span className="muted">{d.filename}</span></div>)}
          {!app.documents?.length && <p className="muted">No documents.</p>}
        </div>
      </div>

      {confirm && (
        <Modal title="Withdraw application?" onClose={() => setConfirm(false)}>
          <p>This cannot be undone.</p>
          <div className="row">
            <button className="btn danger" onClick={() => act('withdraw', 'Application withdrawn')}>Yes, withdraw</button>
            <button className="btn secondary" onClick={() => setConfirm(false)}>Cancel</button>
          </div>
        </Modal>
      )}
    </>
  );
}
