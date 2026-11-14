import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../../api';
import { Loading, ErrorBox, StatusBadge, Field, useToast } from '../../components/ui';

// Scores must add up to 100: 40 + 40 + 20.
const CRITERIA = [['academic', 'Academic merit', 40], ['financial_need', 'Financial need', 40], ['other', 'Other criteria', 20]];

export default function ReviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [app, setApp] = useState(null);
  const [error, setError] = useState(null);
  const [scores, setScores] = useState({ academic: '', financial_need: '', other: '' });
  const [remarks, setRemarks] = useState('');
  const [errors, setErrors] = useState({});

  useEffect(() => { api.get(`/applications/${id}`).then(setApp).catch(setError); }, [id]);

  const total = Object.values(scores).reduce((a, b) => a + (Number(b) || 0), 0);

  const submit = async (decision) => {
    const bad = {};
    CRITERIA.forEach(([k, , max]) => {
      const v = Number(scores[k]);
      if (scores[k] === '' || v < 0 || v > max) bad[k] = `Enter 0–${max}`;
    });
    setErrors(bad);
    if (Object.keys(bad).length) return;
    try {
      await api.post(`/reviewer/applications/${id}/review`, {
        scores: Object.fromEntries(CRITERIA.map(([k]) => [k, Number(scores[k])])), decision, remarks,
      });
      toast('Review submitted');
      navigate('/reviewer');
    } catch (err) { setErrors(err.fields || {}); toast(err.message, 'error'); }
  };

  if (error) return <ErrorBox error={error} />;
  if (!app) return <Loading />;
  const canReview = app.status === 'VERIFIED';

  return (
    <>
      <h1>{app.student_name} — {app.scholarship_title} <StatusBadge status={app.status} /></h1>
      <div className="split">
        <div className="card">
          <h2>Application</h2>
          {['profile', 'institution', 'address'].map((s) => (
            <div key={s} style={{ marginBottom: 10 }}>
              <strong style={{ textTransform: 'capitalize' }}>{s}</strong>
              {Object.entries(app[s] || {}).map(([k, v]) => <div key={k} className="muted">{k.replaceAll('_', ' ')}: {String(v)}</div>)}
            </div>
          ))}
        </div>
        <div className="card">
          <h2>Scoring (total {total}/100)</h2>
          {CRITERIA.map(([k, label, max]) => (
            <Field key={k} name={k} label={`${label} (0–${max})`} type="number" min={0} max={max}
              value={scores[k]} onChange={(n, v) => setScores({ ...scores, [n]: v })} error={errors[k]} disabled={!canReview} />
          ))}
          <Field label="Remarks" name="remarks" type="textarea" value={remarks} onChange={(_, v) => setRemarks(v)} disabled={!canReview} />
          {canReview ? (
            <div className="row">
              <button className="btn" onClick={() => submit('APPROVED')}>Approve</button>
              <button className="btn secondary" onClick={() => submit('CHANGES_REQUESTED')}>Request changes</button>
              <button className="btn danger" onClick={() => submit('REJECTED')}>Reject</button>
            </div>
          ) : <p className="muted">This application has already been reviewed.</p>}
        </div>
      </div>
    </>
  );
}
