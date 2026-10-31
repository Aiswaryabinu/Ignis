import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { useCustomers } from '../api/useCustomers.js';
import apiClient from '../../../lib/apiClient.js';
import { downloadCsv } from '../../../lib/exportCsv.js';

const demoCustomers = [
  {
    id: 1,
    name: 'Northwind Traders',
    email: 'ops@northwind.in',
    phone: '+91 98765 43210',
    industry: 'Retail',
    subscriptions: 2,
    status: 'Active',
    location: 'Mumbai, Maharashtra',
    joined: 'Jan 12, 2024',
    revenue: '₹1,24,000',
    contact: 'Rahul Mehta',
  },
  {
    id: 2,
    name: 'Kerala Foods Co.',
    email: 'it@keralafoods.in',
    phone: '+91 91234 56789',
    industry: 'Food & Beverage',
    subscriptions: 1,
    status: 'Active',
    location: 'Kochi, Kerala',
    joined: 'Mar 5, 2024',
    revenue: '₹62,500',
    contact: 'Priya Nair',
  },
  {
    id: 3,
    name: 'Tidewater Logistics',
    email: 'admin@tidewater.in',
    phone: '+91 87654 32109',
    industry: 'Logistics',
    subscriptions: 1,
    status: 'Active',
    location: 'Chennai, Tamil Nadu',
    joined: 'Feb 19, 2024',
    revenue: '₹48,000',
    contact: 'Arun Krishnan',
  },
  {
    id: 4,
    name: 'Lumen Clinics',
    email: 'billing@lumen.in',
    phone: '+91 99887 76655',
    industry: 'Healthcare',
    subscriptions: 0,
    status: 'Inactive',
    location: 'Bengaluru, Karnataka',
    joined: 'Apr 2, 2024',
    revenue: '₹0',
    contact: 'Dr. Sneha Rao',
  },
];

function getInitials(name) {
  return name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

export function CustomersPage() {
  const { data = [], isLoading, isError } = useCustomers();
  const queryClient = useQueryClient();
  const exportCustomers = () => downloadCsv('customers.csv', customers.map(({ id, name, email, industry, subscriptions, status }) => ({ id, name, email, industry, subscriptions, status })));
  const customers = data.map((customer) => ({
    ...customer,
    name: customer.name || customer.company_name,
    email: customer.email || customer.billing_email,
    contact: customer.contact || customer.contact_person || '—',
    subscriptions: customer.subscriptions || 0,
    status: customer.status || (customer.is_active ? 'Active' : 'Inactive'),
    industry: customer.industry || '—',
    joined: customer.joined || '—',
    revenue: customer.revenue || '—',
  }));
  // drawerMode: null | 'create' | 'detail'
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saveError, setSaveError] = useState('');

  const isOpen = drawerMode !== null;

  // Push main panel when drawer is open
  useEffect(() => {
    const mainPanel = document.querySelector('.main-panel');
    if (!mainPanel) return;
    if (isOpen) {
      mainPanel.classList.add('drawer-push');
    } else {
      mainPanel.classList.remove('drawer-push');
    }
    return () => mainPanel.classList.remove('drawer-push');
  }, [isOpen]);

  function openCreate() {
    setSelectedCustomer(null);
    setDrawerMode('create');
  }

  function openDetail(customer) {
    setSelectedCustomer(customer);
    setEditing(false);
    setDrawerMode('detail');
  }

  function closeDrawer() {
    setDrawerMode(null);
    setSelectedCustomer(null);
    setEditing(false);
    setSaveError('');
  }

  function startEditing() {
    setForm({
      company_name: selectedCustomer.name,
      contact_person: selectedCustomer.contact || '',
      billing_email: selectedCustomer.email || '',
      phone: selectedCustomer.phone || '',
      industry: selectedCustomer.industry || '',
      is_active: selectedCustomer.status === 'Active',
    });
    setSaveError('');
    setEditing(true);
  }

  async function saveCustomer(event) {
    event.preventDefault();
    try {
      await apiClient.put(`/customers/${selectedCustomer.id}`, form);
      await queryClient.invalidateQueries({ queryKey: ['customers'] });
      setEditing(false);
      setDrawerMode(null);
    } catch (requestError) {
      setSaveError(requestError.response?.data?.detail || 'Unable to save customer.');
    }

    async function createCustomer(event) {
      event.preventDefault();
      const values = new FormData(event.currentTarget);
      try {
        await apiClient.post('/customers', {
          company_name: values.get('company_name'),
          billing_email: values.get('billing_email') || null,
          industry: values.get('industry') || null,
          phone: values.get('phone') || null,
          is_active: true,
        });
        await queryClient.invalidateQueries({ queryKey: ['customers'] });
        closeDrawer();
      } catch (requestError) {
        setSaveError(requestError.response?.data?.detail || 'Unable to create customer.');
      }
    }
  }

  return (
    <AppShell
      title="Customers"
      description="People and companies you bill."
      breadcrumb="Brightloop / Customers"
      activeNav="customers"
      primaryAction={
        <button className="primary-action" type="button" onClick={openCreate}>
          + Create
        </button>
      }
      secondaryAction={
        <button className="secondary-action" type="button" onClick={exportCustomers}>
          Export
        </button>
      }
    >
      {/* ── Drawer Sidebar ─────────────────────────────── */}
      <aside className={`customer-drawer ${isOpen ? 'customer-drawer--open' : ''}`}>
        {drawerMode === 'create' && (
          <>
            <div className="drawer-header">
              <div className="drawer-title-group">
                <span className="drawer-eyebrow">New Record</span>
                <h2 className="drawer-title">Create Customer</h2>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />
            <p className="drawer-subtitle">Fill in the details below to add a new customer.</p>

            <form
              className="drawer-form"
              onSubmit={createCustomer}
            >
              <label className="drawer-field">
                <span className="drawer-field-label">Full Name</span>
                <input name="company_name" type="text" className="drawer-input" placeholder="e.g. Acme Corp" required />
              </label>
              <label className="drawer-field">
                <span className="drawer-field-label">Email Address</span>
                <input name="billing_email" type="email" className="drawer-input" placeholder="e.g. billing@acme.in" />
              </label>
              <label className="drawer-field">
                <span className="drawer-field-label">Industry</span>
                <input name="industry" type="text" className="drawer-input" placeholder="e.g. Retail, SaaS…" />
              </label>
              <label className="drawer-field">
                <span className="drawer-field-label">Phone (optional)</span>
                <input name="phone" type="tel" className="drawer-input" placeholder="e.g. +91 98765 43210" />
              </label>
              {saveError && <p className="form-error" role="alert">{saveError}</p>}
              <div className="drawer-actions">
                <button type="submit" className="drawer-save-btn">Save Customer</button>
                <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Cancel</button>
              </div>
            </form>
          </>
        )}

        {drawerMode === 'detail' && selectedCustomer && !editing && (
          <>
            {/* Header with avatar */}
            <div className="drawer-detail-header">
              <div className="drawer-detail-avatar">
                {getInitials(selectedCustomer.name)}
              </div>
              <div className="drawer-detail-title-group">
                <span className="drawer-eyebrow">{selectedCustomer.industry}</span>
                <h2 className="drawer-title">{selectedCustomer.name}</h2>
                <span className={`status-pill ${selectedCustomer.status === 'Active' ? 'success' : 'muted'}`} style={{ marginTop: '6px', display: 'inline-flex' }}>
                  <span className="dot" />
                  {selectedCustomer.status}
                </span>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />

            {/* Stats row */}
            <div className="drawer-stats-row">
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedCustomer.subscriptions}</span>
                <span className="drawer-stat-label">Subscriptions</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedCustomer.revenue}</span>
                <span className="drawer-stat-label">Revenue</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedCustomer.joined.split(' ')[2] || selectedCustomer.joined}</span>
                <span className="drawer-stat-label">Member Since</span>
              </div>
            </div>

            <div className="drawer-divider" />

            {/* Detail fields */}
            <div className="drawer-detail-body">
              <div className="drawer-detail-section-label">Contact Details</div>

              <div className="drawer-detail-grid">
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Contact Person</span>
                  <span className="drawer-detail-val">{selectedCustomer.contact}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Email</span>
                  <a href={`mailto:${selectedCustomer.email}`} className="drawer-detail-val drawer-detail-link">
                    {selectedCustomer.email}
                  </a>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Phone</span>
                  <span className="drawer-detail-val">{selectedCustomer.phone}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Location</span>
                  <span className="drawer-detail-val">{selectedCustomer.location}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Industry</span>
                  <span className="drawer-detail-val">{selectedCustomer.industry}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Joined</span>
                  <span className="drawer-detail-val">{selectedCustomer.joined}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="drawer-actions" style={{ marginTop: 'auto' }}>
              <button type="button" className="drawer-save-btn" onClick={startEditing}>Edit Customer</button>
              <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Close</button>
            </div>
          </>
        )}
        {drawerMode === 'detail' && selectedCustomer && editing && (
          <form className="drawer-form" onSubmit={saveCustomer}>
            <div className="drawer-header">
              <div className="drawer-title-group"><span className="drawer-eyebrow">Edit record</span><h2 className="drawer-title">Edit Customer</h2></div>
              <button type="button" className="drawer-close-btn" onClick={() => setEditing(false)} aria-label="Close">✕</button>
            </div>
            <label className="drawer-field"><span className="drawer-field-label">Company name</span><input className="drawer-input" value={form.company_name || ''} onChange={(event) => setForm({ ...form, company_name: event.target.value })} required /></label>
            <label className="drawer-field"><span className="drawer-field-label">Contact person</span><input className="drawer-input" value={form.contact_person || ''} onChange={(event) => setForm({ ...form, contact_person: event.target.value })} /></label>
            <label className="drawer-field"><span className="drawer-field-label">Email</span><input className="drawer-input" type="email" value={form.billing_email || ''} onChange={(event) => setForm({ ...form, billing_email: event.target.value })} /></label>
            <label className="drawer-field"><span className="drawer-field-label">Phone</span><input className="drawer-input" value={form.phone || ''} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
            <label className="drawer-field"><span className="drawer-field-label">Industry</span><input className="drawer-input" value={form.industry || ''} onChange={(event) => setForm({ ...form, industry: event.target.value })} /></label>
            {saveError && <p className="form-error" role="alert">{saveError}</p>}
            <div className="drawer-actions"><button type="submit" className="drawer-save-btn">Save changes</button><button type="button" className="drawer-cancel-btn" onClick={() => setEditing(false)}>Cancel</button></div>
          </form>
        )}
      </aside>

      {/* ── Main Table ─────────────────────────────────── */}
      <div className="customers-layout">
        <div className="customers-list-panel">
          <div className="table-toolbar">
            <div className="search-box">Search customers...</div>
            <div className="filter-select">All statuses ⌄</div>
          </div>

          <div className="data-card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Email</th>
                  <th>Industry</th>
                  <th>Subscriptions</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {isLoading && <tr><td colSpan="5">Loading customers…</td></tr>}
                {isError && <tr><td colSpan="5">Unable to load customers. Check that the API is running.</td></tr>}
                {!isLoading && !isError && customers.map((customer) => (
                  <tr
                    key={customer.id}
                    className={`customer-row ${selectedCustomer?.id === customer.id ? 'customer-row--active' : ''}`}
                    onClick={() => openDetail(customer)}
                  >
                    <td className="customer-name">{customer.name}</td>
                    <td>{customer.email}</td>
                    <td>{customer.industry}</td>
                    <td>{customer.subscriptions}</td>
                    <td>
                      <span className={`status-pill ${customer.status === 'Active' ? 'success' : 'muted'}`}>
                        <span className="dot" />
                        {customer.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="table-footer">Showing {customers.length} records</div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
