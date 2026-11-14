import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../../api';
import { Field, FileUpload, Loading, ErrorBox, useToast } from '../../components/ui';

// Each form step = which endpoint to PUT to + which fields it has.
const SECTIONS = {
  profile: { label: 'Profile', fields: [['full_name', 'Full name'], ['date_of_birth', 'Date of birth', 'date'], ['phone', 'Phone'], ['government_id_number', 'Government ID number']] },
  institution: { label: 'Institution', fields: [['institution_name', 'Institution name'], ['registration_number', 'Registration number'], ['enrollment_number', 'Enrollment number']] },
  address: { label: 'Address', fields: [['address_line', 'Address line'], ['city', 'City'], ['state', 'State'], ['postal_code', 'Postal code']] },
  bank: { label: 'Bank', fields: [['account_holder_name', 'Account holder name'], ['account_number', 'Account number'], ['ifsc', 'IFSC code']] },
};
// Order of wizard steps. "proofs", "declaration" and "review" are special (not plain forms).
const STEPS = ['profile', 'institution', 'proofs', 'address', 'bank', 'declaration', 'review'];
const LABELS = { ...Object.fromEntries(Object.entries(SECTIONS).map(([k, v]) => [k, v.label])), proofs: 'Proofs', declaration: 'Declaration', review: 'Review & submit' };

export default function ApplyWizard() {
  const { scholarshipId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [app, setApp] = useState(null);
  const [error, setError] = useState(null);
  const [step, setStep] = useState(0);
  const [data, setData] = useState({});        // { profile: {...}, institution: {...}, ... }
  const [errors, setErrors] = useState({});
  const [declared, setDeclared] = useState(false);
  const [busy, setBusy] = useState(false);

  // Create (or fetch the existing) draft for this scholarship.
  useEffect(() => {
    api.post('/applications', { scholarship_id: scholarshipId })
      .then(async (created) => {
        const full = await api.get(`/applications/${created.id}`);
        setApp(full);
        setData({ profile: full.profile || {}, institution: full.institution || {}, address: full.address || {}, bank: full.bank || {} });
      })
      .catch(setError);
  }, [scholarshipId]);

  if (error) return <ErrorBox error={error} />;
  if (!app) return <Loading />;

  const key = STEPS[step];
  const doc = (type) => app.documents?.find((d) => d.doc_type === type);
  const refreshDocs = async () => setApp(await api.get(`/applications/${app.id}`));
  const setField = (name, value) => setData((d) => ({ ...d, [key]: { ...d[key], [name]: value } }));

  // Save the current section to the backend. Returns true if it worked.
  const save = async () => {
    if (!SECTIONS[key]) return true;
    setBusy(true); setErrors({});
    try {
      await api.put(`/applications/${app.id}/${key}`, data[key] || {});
      return true;
    } catch (err) {
      setErrors(err.fields || {});
      toast(err.message, 'error');
      return false;
    } finally { setBusy(false); }
  };

  const next = async () => { if (await save()) setStep((s) => Math.min(s + 1, STEPS.length - 1)); };
  const saveDraft = async () => { if (await save()) toast('Draft saved'); };

  const finish = async () => {
    setBusy(true);
    try {
      const resubmitting = app.status === 'CHANGES_REQUESTED';
      await api.post(`/applications/${app.id}/${resubmitting ? 'resubmit' : 'submit'}`, { declaration_accepted: true });
      toast('Application submitted!');
      navigate(`/student/applications/${app.id}`);
    } catch (err) { toast(err.message, 'error'); }
    finally { setBusy(false); }
  };

  return (
    <>
      <h1>Apply: {app.scholarship_title}</h1>
      <div className="stepper">
        {STEPS.map((s, i) => <span key={s} className={i === step ? 'active' : i < step ? 'done' : ''}>{i + 1}. {LABELS[s]}</span>)}
      </div>

      <div className="card">
        {SECTIONS[key] && SECTIONS[key].fields.map(([name, label, type]) => (
          <Field key={name} name={name} label={label} type={type} value={data[key]?.[name]} onChange={setField} error={errors[name]} />
        ))}

        {key === 'bank' && (
          <FileUpload label="Cancelled cheque" docType="cancelled_cheque" applicationId={app.id} existing={doc('cancelled_cheque')} onUploaded={refreshDocs} />
        )}

        {key === 'proofs' && (
          <>
            <FileUpload label="Government ID" docType="government_id" applicationId={app.id} existing={doc('government_id')} onUploaded={refreshDocs} />
            <FileUpload label="Address proof" docType="address_proof" applicationId={app.id} existing={doc('address_proof')} onUploaded={refreshDocs} />
          </>
        )}

        {key === 'declaration' && (
          <label>
            <input type="checkbox" checked={declared} onChange={(e) => setDeclared(e.target.checked)} />{' '}
            I declare that all information and documents I provided are true and correct.
          </label>
        )}

        {key === 'review' && (
          <>
            {['profile', 'institution', 'address', 'bank'].map((s) => (
              <div key={s} style={{ marginBottom: 12 }}>
                <h2>{LABELS[s]}</h2>
                {SECTIONS[s].fields.map(([n, l]) => <div key={n} className="muted">{l}: <strong style={{ color: 'var(--text)' }}>{data[s]?.[n] || '—'}</strong></div>)}
              </div>
            ))}
            <h2>Documents</h2>
            {['government_id', 'address_proof', 'cancelled_cheque'].map((t) => (
              <div key={t} className="muted">{t.replaceAll('_', ' ')}: {doc(t) ? '✔ ' + doc(t).filename : '✘ missing'}</div>
            ))}
          </>
        )}
      </div>

      <div className="row">
        <button className="btn secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>Back</button>
        {SECTIONS[key] && <button className="btn secondary" disabled={busy} onClick={saveDraft}>Save draft</button>}
        {key !== 'review'
          ? <button className="btn" disabled={busy || (key === 'declaration' && !declared)} onClick={next}>Next</button>
          : <button className="btn" disabled={busy || !declared} onClick={finish}>Submit application</button>}
      </div>
      {key === 'review' && !declared && <p className="muted">Go back to the Declaration step and tick the box first.</p>}
    </>
  );
}
