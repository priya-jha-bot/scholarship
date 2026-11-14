import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../../api';
import { Loading, ErrorBox, StatusBadge, Field, useToast } from '../../components/ui';

const CHECKLIST = [
  ['identity_matches', 'Government ID matches the profile'],
  ['address_matches', 'Address proof matches the address'],
  ['institution_verified', 'Institution is verified'],
  ['bank_proof_valid', 'Cancelled cheque matches bank details'],
];

export default function VerifyApplication() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [app, setApp] = useState(null);
  const [error, setError] = useState(null);
  const [checks, setChecks] = useState({});
  const [remarks, setRemarks] = useState('');
  const [docUrl, setDocUrl] = useState('');

  useEffect(() => { api.get(`/applications/${id}`).then(setApp).catch(setError); }, [id]);

  // Signed links last 10 minutes, so fetch one only when the admin clicks.
  const openDoc = async (docId) => {
    try { setDocUrl((await api.get(`/documents/${docId}/link`)).url); }
    catch (err) { toast(err.message, 'error'); }
  };

  const decide = async (decision) => {
    try {
      await api.post(`/admin/applications/${id}/verify`, { decision, checklist: checks, remarks });
      toast(decision === 'VERIFIED' ? 'Application verified' : 'Application rejected');
      navigate('/admin');
    } catch (err) { toast(err.message, 'error'); }
  };

  if (error) return <ErrorBox error={error} />;
  if (!app) return <Loading />;
  const allChecked = CHECKLIST.every(([k]) => checks[k]);
  const canDecide = app.status === 'SUBMITTED';

  return (
    <>
      <h1>{app.student_name} — {app.scholarship_title} <StatusBadge status={app.status} /></h1>
      <div className="split">
        <div className="card">
          <h2>Documents</h2>
          {(app.documents || []).map((d) => (
            <div key={d.id} className="row" style={{ marginBottom: 6 }}>
              <span>{d.doc_type.replaceAll('_', ' ')}</span>
              <button className="btn secondary" onClick={() => openDoc(d.id)}>View</button>
            </div>
          ))}
          {docUrl && <iframe className="viewer" src={docUrl} title="Document viewer" />}
        </div>
        <div className="card">
          <h2>Checklist</h2>
          {CHECKLIST.map(([k, label]) => (
            <label key={k} style={{ display: 'block', marginBottom: 8 }}>
              <input type="checkbox" disabled={!canDecide} checked={!!checks[k]} onChange={(e) => setChecks({ ...checks, [k]: e.target.checked })} /> {label}
            </label>
          ))}
          <Field label="Remarks" name="remarks" type="textarea" value={remarks} onChange={(_, v) => setRemarks(v)} />
          {canDecide ? (
            <div className="row">
              <button className="btn" disabled={!allChecked} onClick={() => decide('VERIFIED')}>Verify</button>
              <button className="btn danger" onClick={() => decide('REJECTED_BY_ADMIN')}>Reject</button>
            </div>
          ) : <p className="muted">This application is no longer awaiting verification.</p>}
        </div>
      </div>
    </>
  );
}
