import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { useState } from 'react';

import { AppShell } from '../components/layout/AppShell.jsx';
import { CustomersPage } from '../features/customers/pages/CustomersPage.jsx';
import { InvoicesPage } from '../features/invoices/pages/InvoicesPage.jsx';
import { DiscountsPage } from '../features/discounts/pages/DiscountsPage.jsx';
import { PaymentsPage } from '../features/payments/pages/PaymentsPage.jsx';
import { DashboardPage } from '../features/dashboard/pages/DashboardPage.jsx';
import { ReportsPage } from '../features/reports/pages/ReportsPage.jsx';
import { SettingsPage } from '../features/settings/pages/SettingsPage.jsx';
import { PlansPage } from '../features/plans/pages/PlansPage.jsx';
import { ProductsPage } from '../features/products/pages/ProductsPage.jsx';
import { QuotationsPage } from '../features/quotations/pages/QuotationsPage.jsx';
import { SubscriptionsPage } from '../features/subscriptions/pages/SubscriptionsPage.jsx';
import { ProfilePage } from '../features/profile/pages/ProfilePage.jsx';
import { TaxesPage } from '../features/taxes/pages/TaxesPage.jsx';
import { CustomerDashboardPage } from '../features/dashboard/pages/CustomerDashboardPage.jsx';
import { useAuth } from './providers.jsx';

function RequireRole({ allowedRoles, children }) {
  const { user, loading } = useAuth();

  if (loading) return <div className="page-shell"><p>Loading your workspace…</p></div>;

  if (!user) {
    return <Navigate to="/auth/signin" replace />;
  }

  const role = user.role.charAt(0) + user.role.slice(1).toLowerCase();
  if (!allowedRoles.includes(role)) {
    return <Navigate to={role === 'Customer' ? '/subscriptions' : '/dashboard'} replace />;
  }

  return children;
}

function SignInPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    const form = new FormData(event.currentTarget);
    try {
      const user = await login({ email: form.get('email'), password: form.get('password') });
      navigate(userLandingPath(user), { replace: true });
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to sign in.');
    } finally {
      setSubmitting(false);
    }

    function userLandingPath(user) {
      return user?.role === 'CUSTOMER' ? '/customer-dashboard' : '/dashboard';
    }
  }

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

        <form className="auth-form" onSubmit={submit}>
          <label className="field-group">
            <span>Email</span>
            <input name="email" type="email" defaultValue="admin@brightloop.io" required />
          </label>

          <label className="field-group">
            <span>Password</span>
            <input name="password" type="password" defaultValue="password123" required />
          </label>

          <div className="form-row">
            <label className="remember-me">
              <input type="checkbox" defaultChecked />
              <span>Remember me</span>
            </label>
            <a href="/auth/forgot-password">Forgot password?</a>
          </div>

          {error && <p role="alert" className="form-error">{error}</p>}
          <button type="submit" className="primary-button" disabled={submitting}>{submitting ? 'Signing in…' : 'Sign in'}</button>

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

  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (form.get('password') !== form.get('confirm_password')) {
      setError('Passwords do not match.');
      return;
    }
    try {
      await register({
        email: form.get('email'),
        password: form.get('password'),
        full_name: form.get('full_name'),
        company_name: form.get('company_name'),
      });
      navigate(userLandingPath({ role: 'CUSTOMER' }), { replace: true });
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to create account.');
    }
  }

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

        <form className="auth-form" onSubmit={submit}>
          <label className="field-group">
            <span>Full name</span>
            <input name="full_name" type="text" defaultValue="Aisha Khan" required />
          </label>

          <label className="field-group">
            <span>Email</span>
            <input name="email" type="email" defaultValue="aisha@brightloop.io" required />
          </label>

          <label className="field-group">
            <span>Password</span>
            <input name="password" type="password" defaultValue="password123" required />
          </label>

          <label className="field-group">
            <span>Confirm password</span>
            <input name="confirm_password" type="password" defaultValue="password123" required />
          </label>

          <label className="field-group">
            <span>Company name</span>
            <input name="company_name" type="text" defaultValue="Brightloop" required />
          </label>
          {error && <p role="alert" className="form-error">{error}</p>}
          <button type="submit" className="primary-button">Create account</button>

          <p className="auth-link-row">
            Already have an account? <a href="/auth/signin">Sign in</a>
          </p>
        </form>
      </div>
    </div>
  );
}

function ForgotPasswordPage() {
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

        <form className="auth-form">
          <label className="field-group">
            <span>Email address</span>
            <input type="email" defaultValue="admin@brightloop.io" />
          </label>

          <button type="submit" className="primary-button">Send reset link</button>

          <p className="auth-link-row">
            Back to <a href="/auth/signin">Sign in</a>
          </p>
        </form>
      </div>
    </div>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/auth/signin" element={<SignInPage />} />
      <Route path="/auth/signup" element={<SignUpPage />} />
      <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />

      <Route path="/dashboard" element={<RequireRole allowedRoles={['Admin', 'Staff']}><DashboardPage /></RequireRole>} />
      <Route path="/customer-dashboard" element={<RequireRole allowedRoles={['Customer']}><CustomerDashboardPage /></RequireRole>} />

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
          <RequireRole allowedRoles={['Admin', 'Staff', 'Customer']}>
            <QuotationsPage />
          </RequireRole>
        }
      />

      <Route
        path="/subscriptions"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff', 'Customer']}>
            <SubscriptionsPage />
          </RequireRole>
        }
      />

      <Route
        path="/invoices"
        element={
          <RequireRole allowedRoles={['Admin', 'Staff', 'Customer']}>
            <InvoicesPage />
          </RequireRole>
        }
      />

      <Route path="/discounts" element={<RequireRole allowedRoles={['Admin', 'Staff']}><DiscountsPage /></RequireRole>} />
      <Route path="/taxes" element={<RequireRole allowedRoles={['Admin']}><TaxesPage /></RequireRole>} />
      <Route path="/payments" element={<RequireRole allowedRoles={['Admin', 'Staff', 'Customer']}><PaymentsPage /></RequireRole>} />
      <Route path="/reports" element={<RequireRole allowedRoles={['Admin', 'Staff']}><ReportsPage /></RequireRole>} />
      <Route path="/staff-users" element={<RequireRole allowedRoles={['Admin']}><SettingsPage /></RequireRole>} />
      <Route path="/settings" element={<RequireRole allowedRoles={['Admin', 'Staff', 'Customer']}><ProfilePage /></RequireRole>} />

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
