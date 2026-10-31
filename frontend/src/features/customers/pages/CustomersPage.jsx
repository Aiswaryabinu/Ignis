import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import apiClient from '../../../lib/apiClient';

function getInitials(name = '') {
  return name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
}

function formatDate(value) {
  if (!value || value === '—') return '—';
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(value));
}

export function CustomersPage() {
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [query, setQuery] = useState('');
  const queryClient = useQueryClient();
  const { data: customers = [], isLoading, error } = useQuery({
    queryKey: ['customers'],
    queryFn: async () => (await apiClient.get('/customers')).data,
  });
  const createCustomer = useMutation({
    mutationFn: async (payload) => (await apiClient.post('/customers', payload)).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['customers'] });
      setDrawerMode(null);
    },
  });

  useEffect(() => {
    const mainPanel = document.querySelector('.main-panel');
    if (!mainPanel) return undefined;
    mainPanel.classList.toggle('drawer-push', drawerMode !== null);
    return () => mainPanel.classList.remove('drawer-push');
  }, [drawerMode]);

  const filteredCustomers = useMemo(() => customers.filter((customer) =>
    [customer.name, customer.email, customer.industry].some((value) =>
      (value || '').toLowerCase().includes(query.toLowerCase()))), [customers, query]);

  function closeDrawer() {
    setDrawerMode(null);
    setSelectedCustomer(null);
  }

  function submitCustomer(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    createCustomer.mutate({
      company_name: form.get('company_name').trim(),
      billing_email: form.get('billing_email') || null,
      contact_person: form.get('contact_person') || null,
      industry: form.get('industry') || null,
      phone: form.get('phone') || null,
    });
  }

  return (
    <AppShell
      title="Customers"
      description="People and companies you bill."
      breadcrumb="Brightloop / Customers"
      activeNav="customers"
      primaryAction={<button className="primary-action" type="button" onClick={() => setDrawerMode('create')}>+ Create</button>}
    >
      <aside className={`customer-drawer ${drawerMode ? 'customer-drawer--open' : ''}`}>
        {drawerMode === 'create' && <>
          <div className="drawer-header">
            <div className="drawer-title-group"><span className="drawer-eyebrow">New Record</span><h2 className="drawer-title">Create Customer</h2></div>
            <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">✕</button>
          </div>
          <div className="drawer-divider" />
          <p className="drawer-subtitle">Fill in the details below to add a new customer.</p>
          <form className="drawer-form" onSubmit={submitCustomer}>
            <label className="drawer-field"><span className="drawer-field-label">Company / Full Name</span><input name="company_name" className="drawer-input" placeholder="e.g. Acme Corp" required /></label>
            <label className="drawer-field"><span className="drawer-field-label">Email Address</span><input name="billing_email" type="email" className="drawer-input" placeholder="e.g. billing@acme.in" /></label>
            <label className="drawer-field"><span className="drawer-field-label">Contact Person</span><input name="contact_person" className="drawer-input" placeholder="Contact name" /></label>
            <label className="drawer-field"><span className="drawer-field-label">Industry</span><input name="industry" className="drawer-input" placeholder="e.g. Retail, SaaS" /></label>
            <label className="drawer-field"><span className="drawer-field-label">Phone (optional)</span><input name="phone" type="tel" className="drawer-input" placeholder="e.g. +91 98765 43210" /></label>
            {createCustomer.error && <p role="alert">{createCustomer.error.response?.data?.detail || 'Could not save customer.'}</p>}
            <div className="drawer-actions">
              <button type="submit" className="drawer-save-btn" disabled={createCustomer.isPending}>{createCustomer.isPending ? 'Saving…' : 'Save Customer'}</button>
              <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Cancel</button>
            </div>
          </form>
        </>}
        {drawerMode === 'detail' && selectedCustomer && <>
          <div className="drawer-detail-header">
            <div className="drawer-detail-avatar">{getInitials(selectedCustomer.name)}</div>
            <div className="drawer-detail-title-group"><span className="drawer-eyebrow">{selectedCustomer.industry}</span><h2 className="drawer-title">{selectedCustomer.name}</h2>
              <span className={`status-pill ${selectedCustomer.status === 'Active' ? 'success' : 'muted'}`}><span className="dot" />{selectedCustomer.status}</span>
            </div>
            <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">✕</button>
          </div>
          <div className="drawer-divider" />
          <div className="drawer-stats-row">
            <div className="drawer-stat"><span className="drawer-stat-value">{selectedCustomer.subscriptions}</span><span className="drawer-stat-label">Subscriptions</span></div>
            <div className="drawer-stat-divider" />
            <div className="drawer-stat"><span className="drawer-stat-value">{selectedCustomer.revenue || '—'}</span><span className="drawer-stat-label">Revenue</span></div>
            <div className="drawer-stat-divider" />
            <div className="drawer-stat"><span className="drawer-stat-value">{formatDate(selectedCustomer.joined)}</span><span className="drawer-stat-label">Member Since</span></div>
          </div>
          <div className="drawer-divider" />
          <div className="drawer-detail-body"><div className="drawer-detail-section-label">Contact Details</div><div className="drawer-detail-grid">
            <div className="drawer-detail-item"><span className="drawer-detail-key">Contact Person</span><span className="drawer-detail-val">{selectedCustomer.contact}</span></div>
            <div className="drawer-detail-item"><span className="drawer-detail-key">Email</span><a href={`mailto:${selectedCustomer.email}`} className="drawer-detail-val drawer-detail-link">{selectedCustomer.email || '—'}</a></div>
            <div className="drawer-detail-item"><span className="drawer-detail-key">Phone</span><span className="drawer-detail-val">{selectedCustomer.phone}</span></div>
            <div className="drawer-detail-item"><span className="drawer-detail-key">Location</span><span className="drawer-detail-val">{selectedCustomer.location}</span></div>
            <div className="drawer-detail-item"><span className="drawer-detail-key">Industry</span><span className="drawer-detail-val">{selectedCustomer.industry}</span></div>
            <div className="drawer-detail-item"><span className="drawer-detail-key">Joined</span><span className="drawer-detail-val">{formatDate(selectedCustomer.joined)}</span></div>
          </div></div>
          <div className="drawer-actions" style={{ marginTop: 'auto' }}><button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Close</button></div>
        </>}
      </aside>

      <div className="customers-layout"><div className="customers-list-panel">
        <div className="table-toolbar">
          <input className="search-box" type="search" placeholder="Search customers..." value={query} onChange={(event) => setQuery(event.target.value)} />
        </div>
        <div className="data-card"><table className="data-table"><thead><tr><th>Customer</th><th>Email</th><th>Industry</th><th>Subscriptions</th><th>Status</th></tr></thead>
          <tbody>
            {isLoading && <tr><td colSpan="5">Loading customers…</td></tr>}
            {error && <tr><td colSpan="5" role="alert">{error.response?.data?.detail || 'Could not load customers.'}</td></tr>}
            {!isLoading && !error && filteredCustomers.map((customer) => <tr key={customer.id} className={`customer-row ${selectedCustomer?.id === customer.id ? 'customer-row--active' : ''}`} onClick={() => { setSelectedCustomer(customer); setDrawerMode('detail'); }}>
              <td className="customer-name">{customer.name}</td><td>{customer.email || '—'}</td><td>{customer.industry}</td><td>{customer.subscriptions}</td>
              <td><span className={`status-pill ${customer.status === 'Active' ? 'success' : 'muted'}`}><span className="dot" />{customer.status}</span></td>
            </tr>)}
            {!isLoading && !error && filteredCustomers.length === 0 && <tr><td colSpan="5">No customers found.</td></tr>}
          </tbody>
        </table><div className="table-footer">Showing {filteredCustomers.length} of {customers.length} records</div></div>
      </div></div>
    </AppShell>
  );
}
