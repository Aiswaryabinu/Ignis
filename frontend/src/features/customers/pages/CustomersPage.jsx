import { useState, useEffect } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';

const customers = [
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
  // drawerMode: null | 'create' | 'detail'
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null);

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
    setDrawerMode('detail');
  }

  function closeDrawer() {
    setDrawerMode(null);
    setSelectedCustomer(null);
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
        <button className="secondary-action" type="button">
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
              onSubmit={(e) => {
                e.preventDefault();
                closeDrawer();
              }}
            >
              <label className="drawer-field">
                <span className="drawer-field-label">Full Name</span>
                <input type="text" className="drawer-input" placeholder="e.g. Acme Corp" />
              </label>
              <label className="drawer-field">
                <span className="drawer-field-label">Email Address</span>
                <input type="email" className="drawer-input" placeholder="e.g. billing@acme.in" />
              </label>
              <label className="drawer-field">
                <span className="drawer-field-label">Industry</span>
                <input type="text" className="drawer-input" placeholder="e.g. Retail, SaaS…" />
              </label>
              <label className="drawer-field">
                <span className="drawer-field-label">Phone (optional)</span>
                <input type="tel" className="drawer-input" placeholder="e.g. +91 98765 43210" />
              </label>
              <div className="drawer-actions">
                <button type="submit" className="drawer-save-btn">Save Customer</button>
                <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Cancel</button>
              </div>
            </form>
          </>
        )}

        {drawerMode === 'detail' && selectedCustomer && (
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
              <button type="button" className="drawer-save-btn">Edit Customer</button>
              <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Close</button>
            </div>
          </>
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
                {customers.map((customer) => (
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
            <div className="table-footer">Showing 4 of 4 records</div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
