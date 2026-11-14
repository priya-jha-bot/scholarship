import { Routes, Route, Navigate } from 'react-router-dom';
import RequireRole from './RequireRole';
import Layout from './components/Layout';

import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import { ForgotPassword, ResetPassword } from './pages/Password';

import StudentDashboard from './pages/student/Dashboard';
import ApplyWizard from './pages/student/ApplyWizard';
import ApplicationDetail from './pages/student/ApplicationDetail';

import AdminDashboard from './pages/admin/Dashboard';
import VerifyApplication from './pages/admin/VerifyApplication';
import Scholarships from './pages/admin/Scholarships';
import CreateUser from './pages/admin/CreateUser';
import Reports from './pages/admin/Reports';

import ReviewerDashboard from './pages/reviewer/Dashboard';
import ReviewPage from './pages/reviewer/ReviewPage';

const guard = (role, el) => <RequireRole roles={[role]}>{el}</RequireRole>;

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        <Route path="/student" element={guard('student', <StudentDashboard />)} />
        <Route path="/student/apply/:scholarshipId" element={guard('student', <ApplyWizard />)} />
        <Route path="/student/applications/:id" element={guard('student', <ApplicationDetail />)} />

        <Route path="/admin" element={guard('admin', <AdminDashboard />)} />
        <Route path="/admin/verify/:id" element={guard('admin', <VerifyApplication />)} />
        <Route path="/admin/scholarships" element={guard('admin', <Scholarships />)} />
        <Route path="/admin/users" element={guard('admin', <CreateUser />)} />
        <Route path="/admin/reports" element={guard('admin', <Reports />)} />

        <Route path="/reviewer" element={guard('reviewer', <ReviewerDashboard />)} />
        <Route path="/reviewer/review/:id" element={guard('reviewer', <ReviewPage />)} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
