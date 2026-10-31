import { Navigate, Route, Routes } from 'react-router-dom';

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
import { useAuth } from './providers.jsx';

function RequireRole({ allowedRoles, children }) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/auth/signin" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to="/customers" replace />;
  }

  return children;
}

function SignInPage() {
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

        <form className="auth-form">
          <label className="field-group">
            <span>Email</span>
            <input type="email" defaultValue="admin@brightloop.io" />
          </label>

          <label className="field-group">
            <span>Password</span>
            <input type="password" defaultValue="password123" />
          </label>

          <div className="form-row">
            <label className="remember-me">
              <input type="checkbox" defaultChecked />
              <span>Remember me</span>
            </label>
            <a href="/auth/forgot-password">Forgot password?</a>
          </div>

          <button type="submit" className="primary-button">Sign in</button>

          <p className="auth-link-row">
            Don’t have an account? <a href="/auth/signup">Create account</a>
          </p>
        </form>
      </div>
    </div>
  );
}

function SignUpPage() {
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

        <form className="auth-form">
          <label className="field-group">
            <span>Full name</span>
            <input type="text" defaultValue="Aisha Khan" />
          </label>

          <label className="field-group">
            <span>Email</span>
            <input type="email" defaultValue="aisha@brightloop.io" />
          </label>

          <label className="field-group">
            <span>Password</span>
            <input type="password" defaultValue="password123" />
          </label>

          <label className="field-group">
            <span>Confirm password</span>
            <input type="password" defaultValue="password123" />
          </label>

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
      <Route path="/" element={<Navigate to="/quotations" replace />} />
      <Route path="/auth/signin" element={<SignInPage />} />
      <Route path="/auth/signup" element={<SignUpPage />} />
      <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />

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
