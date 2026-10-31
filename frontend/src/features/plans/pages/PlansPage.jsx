import { useState, useEffect } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { downloadCsv } from '../../../lib/exportCsv.js';

const plans = [
  {
    id: 1,
    plan: 'Business Monthly',
    product: 'CloudDesk Pro',
    billing: 'Monthly',
    basePrice: '₹18,500',
    minQty: '5',
    renewal: 'Automatic',
    status: 'Active',
  },
  {
    id: 2,
    plan: 'Scale Annual',
    product: 'Analytics Suite',
    billing: 'Yearly',
    basePrice: '₹2,16,000',
    minQty: '10',
    renewal: 'Automatic',
    status: 'Active',
  },
  {
    id: 3,
    plan: 'Secure Weekly',
    product: 'SecureVault',
    billing: 'Weekly',
    basePrice: '₹2,800',
    minQty: '2',
    renewal: 'Manual',
    status: 'Draft',
  },
  {
    id: 4,
    plan: 'Starter Monthly',
    product: 'CloudDesk Pro',
    billing: 'Monthly',
    basePrice: '₹7,500',
    minQty: '1',
    renewal: 'Automatic',
    status: 'Active',
  },
];

const pillClassMap = {
  Active: 'success',
  Draft: 'warning',
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

export function PlansPage() {
  const [planRows, setPlanRows] = useState(plans);
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const exportPlans = () => downloadCsv('subscription-plans.csv', plans);

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
    setSelectedPlan(null);
    setDrawerMode('create');
  }

  function openDetail(plan) {
    setSelectedPlan(plan);
    setDrawerMode('detail');
  }

  function closeDrawer() {
    setDrawerMode(null);
    setSelectedPlan(null);
  }

  return (
    <AppShell
      title="Subscription Plans"
      description="Configure pricing, billing frequencies, and plan rules."
      breadcrumb="Brightloop / Subscription Plans"
      activeNav="Subscription Plans"
      primaryAction={
        <button className="primary-action" type="button" onClick={openCreate}>
          + Create plan
        </button>
      }
      secondaryAction={<button className="secondary-action" onClick={() => downloadCsv('subscription-plans.csv', planRows)}>Export</button>}
    >
      <aside className={`customer-drawer ${isOpen ? 'customer-drawer--open' : ''}`}>
        {drawerMode === 'create' && (
          <>
            <div className="drawer-header">
              <div className="drawer-title-group">
                <span className="drawer-eyebrow">New Record</span>
                <h2 className="drawer-title">{selectedPlan ? 'Edit plan' : 'Create plan'}</h2>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />
            <p className="drawer-subtitle">Configure a new plan with billing and renewal settings.</p>

            <form
              className="drawer-form"
              onSubmit={(e) => {
                e.preventDefault();
                const values = new FormData(e.currentTarget);
                const next = { ...selectedPlan, plan: values.get('plan'), product: values.get('product'), billing: values.get('billing'), basePrice: values.get('basePrice'), minQty: values.get('minQty'), renewal: values.get('renewal'), status: selectedPlan?.status || 'Draft' };
                setPlanRows((current) => selectedPlan ? current.map((item) => item.id === selectedPlan.id ? next : item) : [...current, { ...next, id: Date.now() }]);
                closeDrawer();
              }}
            >
              <label className="drawer-field">
                <span className="drawer-field-label">Plan name</span>
                <input name="plan" type="text" className="drawer-input" defaultValue={selectedPlan?.plan || ''} placeholder="e.g. Growth Monthly" required />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Product</span>
                <select name="product" className="drawer-input" defaultValue={selectedPlan?.product || 'CloudDesk Pro'}>
                  <option>CloudDesk Pro</option>
                  <option>Analytics Suite</option>
                  <option>SecureVault</option>
                </select>
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Billing</span>
                <select name="billing" className="drawer-input" defaultValue={selectedPlan?.billing || 'Monthly'}>
                  <option>Daily</option>
                  <option>Weekly</option>
                  <option>Monthly</option>
                  <option>Yearly</option>
                </select>
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Base price</span>
                <input name="basePrice" type="text" className="drawer-input" defaultValue={selectedPlan?.basePrice || ''} placeholder="₹18,500" required />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Min. quantity</span>
                <input name="minQty" type="text" className="drawer-input" defaultValue={selectedPlan?.minQty || ''} placeholder="5" required />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Renewal</span>
                <select name="renewal" className="drawer-input" defaultValue={selectedPlan?.renewal || 'Automatic'}>
                  <option>Automatic</option>
                  <option>Manual</option>
                </select>
              </label>

              <div className="drawer-actions">
                <button type="submit" className="drawer-save-btn">Save plan</button>
                <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Cancel</button>
              </div>
            </form>
          </>
        )}

        {drawerMode === 'detail' && selectedPlan && (
          <>
            <div className="drawer-detail-header">
              <div className="drawer-detail-avatar">{getInitials(selectedPlan.plan)}</div>
              <div className="drawer-detail-title-group">
                <span className="drawer-eyebrow">Plan</span>
                <h2 className="drawer-title">{selectedPlan.plan}</h2>
                <span className={`status-pill ${pillClassMap[selectedPlan.status] || 'muted'}`} style={{ marginTop: '6px', display: 'inline-flex' }}>
                  <span className="dot" />
                  {selectedPlan.status}
                </span>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />

            <div className="drawer-stats-row">
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedPlan.basePrice}</span>
                <span className="drawer-stat-label">Base price</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedPlan.minQty}</span>
                <span className="drawer-stat-label">Min qty</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedPlan.billing}</span>
                <span className="drawer-stat-label">Billing</span>
              </div>
            </div>

            <div className="drawer-divider" />

            <div className="drawer-detail-body">
              <div className="drawer-detail-section-label">Plan details</div>

              <div className="drawer-detail-grid">
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Plan</span>
                  <span className="drawer-detail-val">{selectedPlan.plan}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Product</span>
                  <span className="drawer-detail-val">{selectedPlan.product}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Billing</span>
                  <span className="drawer-detail-val">{selectedPlan.billing}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Base price</span>
                  <span className="drawer-detail-val">{selectedPlan.basePrice}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Min qty</span>
                  <span className="drawer-detail-val">{selectedPlan.minQty}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Renewal</span>
                  <span className="drawer-detail-val">{selectedPlan.renewal}</span>
                </div>
              </div>
            </div>

            <div className="drawer-actions" style={{ marginTop: 'auto' }}>
              <button type="button" className="drawer-save-btn" onClick={() => setDrawerMode('create')}>Edit plan</button>
              <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Close</button>
            </div>
          </>
        )}
      </aside>

      <div className="customers-layout">
        <div className="customers-list-panel">
          <div className="table-toolbar">
            <div className="search-box">Search subscription plans...</div>
            <div className="filter-select">All statuses ⌄</div>
          </div>

          <div className="data-card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Plan</th>
                  <th>Product</th>
                  <th>Billing</th>
                  <th>Base price</th>
                  <th>Min. qty</th>
                  <th>Renewal</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {planRows.map((item) => (
                  <tr
                    key={item.id}
                    className={`customer-row ${selectedPlan?.id === item.id && drawerMode === 'detail' ? 'customer-row--active' : ''}`}
                    onClick={() => openDetail(item)}
                  >
                    <td className="customer-name">{item.plan}</td>
                    <td>{item.product}</td>
                    <td>{item.billing}</td>
                    <td>{item.basePrice}</td>
                    <td>{item.minQty}</td>
                    <td>{item.renewal}</td>
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

            <div className="table-footer">Showing 4 of 4 records</div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
