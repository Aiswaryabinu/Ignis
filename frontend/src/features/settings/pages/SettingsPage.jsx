import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient';

export function SettingsPage() {
  const [creating, setCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const queryClient = useQueryClient();
  const { data: users = [], isLoading, error } = useQuery({ queryKey: ['users'], queryFn: async () => (await apiClient.get('/users')).data });
  const createStaff = useMutation({
    mutationFn: async (payload) => (await apiClient.post('/users/staff', payload)).data,
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['users'] }); setCreating(false); setErrorMessage(''); },
    onError: (err) => setErrorMessage(err.response?.data?.detail || 'Could not create staff account.'),
  });
  function submit(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    createStaff.mutate({ full_name: data.get('full_name'), email: data.get('email'), password: data.get('password') });
  }

  return <AppShell title="Settings" description="Manage administrator and staff access." breadcrumb="Brightloop / Settings" activeNav="Settings"
    primaryAction={<button className="primary-action" type="button" onClick={() => setCreating((value) => !value)}>{creating ? 'Cancel' : '+ Add staff'}</button>}>
    {creating && <div className="data-card" style={{ padding: 20, marginBottom: 20 }}><form className="drawer-form" onSubmit={submit}>
      <label className="drawer-field"><span className="drawer-field-label">Full name</span><input name="full_name" className="drawer-input" autoComplete="name" required /></label>
      <label className="drawer-field"><span className="drawer-field-label">Email</span><input name="email" type="email" className="drawer-input" autoComplete="email" required /></label>
      <label className="drawer-field"><span className="drawer-field-label">Temporary password</span><input name="password" type="password" className="drawer-input" autoComplete="new-password" minLength="9" required /></label>
      {errorMessage && <p role="alert">{errorMessage}</p>}
      <button className="primary-action" type="submit" disabled={createStaff.isPending}>{createStaff.isPending ? 'Creating…' : 'Create staff account'}</button>
    </form></div>}
    <div className="data-card"><table className="data-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th></tr></thead><tbody>
      {isLoading && <tr><td colSpan="3">Loading accounts…</td></tr>}{error && <tr><td colSpan="3" role="alert">{error.response?.data?.detail || 'Could not load accounts.'}</td></tr>}
      {!isLoading && !error && users.map((user) => <tr key={user.id}><td>{user.name}</td><td>{user.email}</td><td>{user.role}</td></tr>)}
    </tbody></table><div className="table-footer">{users.length} accounts</div></div>
  </AppShell>;
}
