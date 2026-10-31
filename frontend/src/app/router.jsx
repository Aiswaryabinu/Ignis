import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navigate, Route, Routes, useNavigate, useSearchParams } from 'react-router-dom';

import { AppShell } from '../components/layout/AppShell.jsx';
import { CustomersPage } from '../features/customers/pages/CustomersPage.jsx';
import { InvoicesPage } from '../features/invoices/pages/InvoicesPage.jsx';
import { DiscountsPage } from '../features/discounts/pages/DiscountsPage.jsx';
import { PaymentsPage } from '../features/payments/pages/PaymentsPage.jsx';
import { PlansPage } from '../features/plans/pages/PlansPage.jsx';
import { ProductsPage } from '../features/products/pages/ProductsPage.jsx';
import { QuotationsPage } from '../features/quotations/pages/QuotationsPage.jsx';
import { ReportsPage } from '../features/reports/pages/ReportsPage.jsx';
import { SettingsPage } from '../features/settings/pages/SettingsPage.jsx';
import { SubscriptionsPage } from '../features/subscriptions/pages/SubscriptionsPage.jsx';
import apiClient from '../lib/apiClient';
import { useAuth } from './providers.jsx';

function RequireRole({ allowedRoles, children }) {
  const { user, loading } = useAuth();

  if (loading) return <div className="auth-page">Loading account…</div>;

  if (!user) {
    return <Navigate to="/auth/signin" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function DashboardPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['reports', 'dashboard'], queryFn: async () => (await apiClient.get('/reports/dashboard')).data });
  return (
    <AppShell
      title="Dashboard"
      description="Overview, charts, and KPIs."
      breadcrumb="Brightloop / Dashboard"
      activeNav="Overview"
    >
      {isLoading && <p>Loading dashboard…</p>}
      {error && <p role="alert">{error.response?.data?.detail || 'Could not load dashboard.'}</p>}
      {data && <div className="data-card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 20, padding: 20 }}>
        <div><span>Active subscriptions</span><h2>{data.active_subscriptions}</h2></div>
        <div><span>Monthly recurring revenue</span><h2>₹{Number(data.mrr).toLocaleString('en-IN')}</h2></div>
        <div><span>Collected</span><h2>₹{Number(data.collected).toLocaleString('en-IN')}</h2></div>
        <div><span>Outstanding</span><h2>₹{Number(data.outstanding).toLocaleString('en-IN')}</h2></div>
        <div><span>Overdue invoices</span><h2>{data.overdue_count}</h2></div>
      </div>}
    </AppShell>
  );
}

function SignInPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-brand">
          <div className="brand-badge">B</div>
          <span>brightloop</span>
        </div>

        <div className="auth-header">
          <p>Welcome back</p>
          <h1>Sign in</h1>
        </div>

        <form className="auth-form" onSubmit={async (event) => {
          event.preventDefault();
          setError('');
          const form = new FormData(event.currentTarget);
          try {
            await login(form.get('email'), form.get('password'));
            navigate('/dashboard', { replace: true });
          } catch (err) {
            setError(err.response?.data?.detail || 'Could not sign in. Check your connection and try again.');
          }
        }}>
          <label className="field-group">
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>

          <label className="field-group">
            <span>Password</span>
            <input name="password" type="password" autoComplete="current-password" required />
          </label>

          <div className="form-row">
            <label className="remember-me">
              <input type="checkbox" defaultChecked />
              <span>Remember me</span>
            </label>
            <a href="/auth/forgot-password">Forgot password?</a>
          </div>

          <button type="submit" className="primary-button">Sign in</button>
          {error && <p role="alert">{error}</p>}

          <p className="auth-link-row">
            Don’t have an account? <a href="/auth/signup">Create account</a>
          </p>
        </form>
      </div>
    </div>
  );
}

function SignUpPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-brand">
          <div className="brand-badge">B</div>
          <span>brightloop</span>
        </div>

        <div className="auth-header">
          <p>Start today</p>
          <h1>Sign up</h1>
        </div>

        <form className="auth-form" onSubmit={async (event) => {
          event.preventDefault();
          setError('');
          const form = new FormData(event.currentTarget);
          const password = form.get('password');
          if (password !== form.get('confirm_password')) {
            setError('Passwords do not match.');
            return;
          }
          try {
            await register({ full_name: form.get('full_name'), email: form.get('email'), password });
            navigate('/dashboard', { replace: true });
          } catch (err) {
            setError(err.response?.data?.detail || 'Could not create account. Check your connection and try again.');
          }
        }}>
          <label className="field-group">
            <span>Full name</span>
            <input name="full_name" type="text" autoComplete="name" required />
          </label>

          <label className="field-group">
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>

          <label className="field-group">
            <span>Password</span>
            <input name="password" type="password" autoComplete="new-password" required />
          </label>

          <label className="field-group">
            <span>Confirm password</span>
            <input name="confirm_password" type="password" autoComplete="new-password" required />
          </label>

          <button type="submit" className="primary-button">Create account</button>
          {error && <p role="alert">{error}</p>}

          <p className="auth-link-row">
            Already have an account? <a href="/auth/signin">Sign in</a>
          </p>
        </form>
      </div>
    </div>
  );
}

function ForgotPasswordPage() {
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-brand">
          <div className="brand-badge">B</div>
          <span>brightloop</span>
        </div>

        <div className="auth-header">
          <p>Reset access</p>
          <h1>Forgot password?</h1>
        </div>

        <form className="auth-form" onSubmit={async (event) => {
          event.preventDefault();
          setMessage('');
          setError('');
          const form = new FormData(event.currentTarget);
          try {
            const { data } = await apiClient.post('/auth/forgot-password', { email: form.get('email') });
            setMessage(data.reset_token ? `Development reset token: ${data.reset_token}` : data.message);
          } catch (err) {
            setError(err.response?.data?.detail || 'Could not request a reset link.');
          }
        }}>
          <label className="field-group">
            <span>Email address</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>

          <button type="submit" className="primary-button">Send reset link</button>
          {message && <p role="status">{message}</p>}
          {error && <p role="alert">{error}</p>}

          <p className="auth-link-row">
            Back to <a href="/auth/signin">Sign in</a>
          </p>
        </form>
      </div>
    </div>
  );
}

function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const token = searchParams.get('token') || '';
  return <div className="auth-page"><div className="auth-panel">
    <div className="auth-brand"><div className="brand-badge">B</div><span>brightloop</span></div>
    <div className="auth-header"><p>Secure your account</p><h1>Choose a new password</h1></div>
    <form className="auth-form" onSubmit={async (event) => {
      event.preventDefault(); setError(''); setMessage('');
      const form = new FormData(event.currentTarget);
      if (form.get('password') !== form.get('confirm_password')) { setError('Passwords do not match.'); return; }
      try {
        const { data } = await apiClient.post('/auth/reset-password', { token, password: form.get('password') });
        setMessage(data.message);
        window.setTimeout(() => navigate('/auth/signin', { replace: true }), 1200);
      } catch (err) { setError(err.response?.data?.detail || 'Could not reset password.'); }
    }}>
      <label className="field-group"><span>New password</span><input name="password" type="password" minLength="9" autoComplete="new-password" required /></label>
      <label className="field-group"><span>Confirm password</span><input name="confirm_password" type="password" minLength="9" autoComplete="new-password" required /></label>
      <button type="submit" className="primary-button" disabled={!token}>Update password</button>
      {message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
    </form>
  </div></div>;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/quotations" replace />} />
      <Route path="/auth/signin" element={<SignInPage />} />
      <Route path="/auth/signup" element={<SignUpPage />} />
      <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/auth/reset-password" element={<ResetPasswordPage />} />

      <Route
        path="/dashboard"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff', 'Customer']}>
            <DashboardPage />
          </RequireRole>
        }
      />

      <Route
        path="/customers"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff']}>
            <CustomersPage />
          </RequireRole>
        }
      />

      <Route
        path="/products"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff']}>
            <ProductsPage />
          </RequireRole>
        }
      />

      <Route
        path="/plans"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff']}>
            <PlansPage />
          </RequireRole>
        }
      />

      <Route
        path="/quotations"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff']}>
            <QuotationsPage />
          </RequireRole>
        }
      />

      <Route
        path="/subscriptions"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff']}>
            <SubscriptionsPage />
          </RequireRole>
        }
      />

      <Route
        path="/invoices"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff']}>
            <InvoicesPage />
          </RequireRole>
        }
      />

      <Route path="/discounts" element={<RequireRole allowedRoles={['Admin', 'Staff']}><DiscountsPage /></RequireRole>} />
      <Route path="/payments" element={<RequireRole allowedRoles={['Admin', 'Staff']}><PaymentsPage /></RequireRole>} />
      <Route path="/reports" element={<RequireRole allowedRoles={['Admin', 'Staff']}><ReportsPage /></RequireRole>} />

      <Route
        path="/settings"
        element={
          <RequireRole allowedRoles={['Admin']}>
            <SettingsPage />
          </RequireRole>
        }
      />

      <Route path="*" element={<Navigate to="/quotations" replace />} />
    </Routes>
  );
}
