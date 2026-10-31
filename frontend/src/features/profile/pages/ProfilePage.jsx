import { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient.js';
import { useAuth } from '../../../app/providers.jsx';

export function ProfilePage() {
  const { user } = useAuth();
  const [name, setName] = useState(user?.full_name || '');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function save(event) {
    event.preventDefault();
    setMessage('');
    setError('');
    try {
      await apiClient.put('/auth/me', { full_name: name });
      setMessage('Profile updated.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to update your profile.');
    }
  }

  return (
    <AppShell title="My Profile" description="Manage your account details." breadcrumb="Brightloop / My Profile" activeNav="profile">
      <div className="data-card form-drawer">
        <form className="drawer-form" onSubmit={save}>
          <label className="field-group">
            <span>Full name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>
          <label className="field-group">
            <span>Email</span>
            <input value={user?.email || ''} readOnly />
          </label>
          <label className="field-group">
            <span>Role</span>
            <input value={user?.role || ''} readOnly />
          </label>
          {message && <p role="status">{message}</p>}
          {error && <p role="alert" className="form-error">{error}</p>}
          <button className="primary-action" type="submit">Save profile</button>
        </form>
      </div>
    </AppShell>
  );
}
