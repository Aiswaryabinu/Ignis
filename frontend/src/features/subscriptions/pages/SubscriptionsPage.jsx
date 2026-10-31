import { useState, useEffect } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';

const subscriptions = [
  {
    id: 1,
    number: 'SUB-0001',
    customer: 'Northwind Traders',
    plan: 'Business Monthly',
    start: '01 Jun 2026',
    expiry: '31 May 2027',
    terms: 'Net 15',
    amount: '₹92,500',
    status: 'Active',
  },
  {
    id: 2,
    number: 'SUB-0002',
    customer: 'Kerala Foods Co.',
    plan: 'Scale Annual',
    start: '15 Mar 2026',
    expiry: '14 Mar 2027',
    terms: 'Net 30',
    amount: '₹16,000',
    status: 'Active',
  },
  {
    id: 3,
    number: 'SUB-0003',
    customer: 'Tidewater Logistics',
    plan: 'Starter Monthly',
    start: '01 Oct 2026',
    expiry: '30 Sep 2027',
    terms: 'Immediate',
    amount: '₹7,500',
    status: 'Confirmed',
  },
  {
    id: 4,
    number: 'SUB-0004',
    customer: 'Northwind Traders',
    plan: 'Secure Weekly',
    start: '—',
    expiry: '—',
    terms: 'Net 15',
    amount: '₹5,600',
    status: 'Quotation',
  },
  {
    id: 5,
    number: 'SUB-0005',
    customer: 'Lumen Clinics',
    plan: 'Starter Monthly',
    start: '01 Jan 2026',
    expiry: '31 Dec 2026',
    terms: 'Net 15',
    amount: '₹7,500',
    status: 'Closed',
  },
];

const pillClassMap = {
  Active: 'success',
  Confirmed: 'info',
  Quotation: 'info',
  Closed: 'muted',
};

function getInitials(name) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

export function SubscriptionsPage() {
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedSubscription, setSelectedSubscription] = useState(null);

  const isOpen = drawerMode !== null;

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
    setSelectedSubscription(null);
    setDrawerMode('create');
  }

  function openDetail(item) {
    setSelectedSubscription(item);
    setDrawerMode('detail');
  }

  function closeDrawer() {
    setDrawerMode(null);
    setSelectedSubscription(null);
  }

  return (
    <AppShell
      title="Subscriptions"
      description="Every subscription and where it stands."
      breadcrumb="Brightloop / Subscriptions"
      activeNav="Subscriptions"
      primaryAction={
        <button className="primary-action" type="button" onClick={openCreate}>
          + New subscription
        </button>
      }
      secondaryAction={<button className="secondary-action">Export</button>}
    >
      <aside className={`customer-drawer ${isOpen ? 'customer-drawer--open' : ''}`}>
        {drawerMode === 'create' && (
          <>
            <div className="drawer-header">
              <div className="drawer-title-group">
                <span className="drawer-eyebrow">New Record</span>
                <h2 className="drawer-title">New subscription</h2>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />
            <p className="drawer-subtitle">Create a new subscription plan assignment.</p>

            <form
              className="drawer-form"
              onSubmit={(e) => {
                e.preventDefault();
                closeDrawer();
              }}
            >
              <label className="drawer-field">
                <span className="drawer-field-label">Customer</span>
                <select className="drawer-input" defaultValue="Northwind Traders">
                  <option>Northwind Traders</option>
                  <option>Kerala Foods Co.</option>
                  <option>Tidewater Logistics</option>
                  <option>Lumen Clinics</option>
                </select>
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Plan</span>
                <select className="drawer-input" defaultValue="Business Monthly">
                  <option>Business Monthly</option>
                  <option>Scale Annual</option>
                  <option>Starter Monthly</option>
                  <option>Secure Weekly</option>
                </select>
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Start date</span>
                <input type="date" className="drawer-input" />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Payment terms</span>
                <select className="drawer-input" defaultValue="Immediate">
                  <option>Immediate</option>
                  <option>Net 15</option>
                  <option>Net 30</option>
                </select>
              </label>

              <div className="drawer-actions">
                <button type="submit" className="drawer-save-btn">Save</button>
                <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Cancel</button>
              </div>
            </form>
          </>
        )}

        {drawerMode === 'detail' && selectedSubscription && (
          <>
            <div className="drawer-detail-header">
              <div className="drawer-detail-avatar">{getInitials(selectedSubscription.customer)}</div>
              <div className="drawer-detail-title-group">
                <span className="drawer-eyebrow">Subscription</span>
                <h2 className="drawer-title">{selectedSubscription.number}</h2>
                <span className={`status-pill ${pillClassMap[selectedSubscription.status] || 'muted'}`} style={{ marginTop: '6px', display: 'inline-flex' }}>
                  <span className="dot" />
                  {selectedSubscription.status}
                </span>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />

            <div className="drawer-stats-row">
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedSubscription.amount}</span>
                <span className="drawer-stat-label">Amount</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedSubscription.start}</span>
                <span className="drawer-stat-label">Starts</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedSubscription.expiry}</span>
                <span className="drawer-stat-label">Expires</span>
              </div>
            </div>

            <div className="drawer-divider" />

            <div className="drawer-detail-body">
              <div className="drawer-detail-section-label">Subscription details</div>

              <div className="drawer-detail-grid">
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Number</span>
                  <span className="drawer-detail-val">{selectedSubscription.number}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Customer</span>
                  <span className="drawer-detail-val">{selectedSubscription.customer}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Plan</span>
                  <span className="drawer-detail-val">{selectedSubscription.plan}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Start</span>
                  <span className="drawer-detail-val">{selectedSubscription.start}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Expiry</span>
                  <span className="drawer-detail-val">{selectedSubscription.expiry}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Terms</span>
                  <span className="drawer-detail-val">{selectedSubscription.terms}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Amount</span>
                  <span className="drawer-detail-val">{selectedSubscription.amount}</span>
                </div>
              </div>
            </div>

            <div className="drawer-actions" style={{ marginTop: 'auto' }}>
              <button type="button" className="drawer-save-btn">Edit subscription</button>
              <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Close</button>
            </div>
          </>
        )}
      </aside>

      <div className="customers-layout">
        <div className="customers-list-panel">
          <div className="table-toolbar">
            <div className="search-box">Search subscriptions...</div>
            <div className="filter-select">All statuses ⌄</div>
          </div>

          <div className="data-card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Customer</th>
                  <th>Plan</th>
                  <th>Start</th>
                  <th>Expiry</th>
                  <th>Terms</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {subscriptions.map((item) => (
                  <tr
                    key={item.id}
                    className={`customer-row ${selectedSubscription?.id === item.id && drawerMode === 'detail' ? 'customer-row--active' : ''}`}
                    onClick={() => openDetail(item)}
                  >
                    <td className="customer-name">{item.number}</td>
                    <td>{item.customer}</td>
                    <td>{item.plan}</td>
                    <td>{item.start}</td>
                    <td>{item.expiry}</td>
                    <td>{item.terms}</td>
                    <td>{item.amount}</td>
                    <td>
                      <span className={`status-pill ${pillClassMap[item.status] || 'muted'}`}>
                        <span className="dot" />
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="table-footer">Showing 5 of 5 records</div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
