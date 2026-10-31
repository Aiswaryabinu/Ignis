import { useState, useEffect } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { downloadCsv } from '../../../lib/exportCsv.js';

const quotations = [
  {
    id: 1,
    template: 'Retail Starter Pack',
    plan: 'Starter Monthly',
    lines: 'CloudDesk Pro × 5',
    validFor: '30 days',
    status: 'Active',
  },
  {
    id: 2,
    template: 'Enterprise Analytics',
    plan: 'Scale Annual',
    lines: 'Analytics Suite × 10',
    validFor: '15 days',
    status: 'Active',
  },
  {
    id: 3,
    template: 'Security Add-on',
    plan: 'Secure Weekly',
    lines: 'SecureVault × 2',
    validFor: '7 days',
    status: 'Draft',
  },
];

function getInitials(name) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

export function QuotationsPage() {
  const [quotationRows, setQuotationRows] = useState(quotations);
  const [drawerMode, setDrawerMode] = useState(null);
  const [selectedQuote, setSelectedQuote] = useState(null);
  const exportQuotations = () => downloadCsv('quotations.csv', quotationRows);

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
    setSelectedQuote(null);
    setDrawerMode('create');
  }

  function openDetail(quote) {
    setSelectedQuote(quote);
    setDrawerMode('detail');
  }

  function closeDrawer() {
    setDrawerMode(null);
    setSelectedQuote(null);
  }

  return (
    <AppShell
      title="Quotations"
      description="Start offers from a template with plan and product lines ready."
      breadcrumb="Brightloop / Quotations"
      activeNav="Quotations"
      primaryAction={
        <button className="primary-action" type="button" onClick={openCreate}>
          + New template
        </button>
      }
      secondaryAction={<button className="secondary-action" onClick={exportQuotations}>Export</button>}
    >
      <aside className={`customer-drawer ${isOpen ? 'customer-drawer--open' : ''}`}>
        {drawerMode === 'create' && (
          <>
            <div className="drawer-header">
              <div className="drawer-title-group">
                <span className="drawer-eyebrow">New Record</span>
                <h2 className="drawer-title">{selectedQuote ? 'Edit template' : 'New template'}</h2>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />
            <p className="drawer-subtitle">Create a reusable quotation template for your sales team.</p>

            <form
              className="drawer-form"
              onSubmit={(e) => {
                e.preventDefault();
                const values = new FormData(e.currentTarget);
                const next = { ...selectedQuote, template: values.get('template'), plan: values.get('plan'), lines: values.get('lines'), validFor: values.get('validFor'), status: selectedQuote?.status || 'Draft' };
                setQuotationRows((current) => selectedQuote ? current.map((item) => item.id === selectedQuote.id ? next : item) : [...current, { ...next, id: Date.now() }]);
                closeDrawer();
              }}
            >
              <label className="drawer-field">
                <span className="drawer-field-label">Template name</span>
                <input name="template" type="text" className="drawer-input" defaultValue={selectedQuote?.template || ''} placeholder="e.g. Retail Starter Pack" required />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Plan</span>
                <select name="plan" className="drawer-input" defaultValue={selectedQuote?.plan || 'Starter Monthly'}>
                  <option>Starter Monthly</option>
                  <option>Scale Annual</option>
                  <option>Secure Weekly</option>
                </select>
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Lines</span>
                <input name="lines" type="text" className="drawer-input" defaultValue={selectedQuote?.lines || ''} placeholder="CloudDesk Pro × 5" required />
              </label>

              <label className="drawer-field">
                <span className="drawer-field-label">Valid for</span>
                <input name="validFor" type="text" className="drawer-input" defaultValue={selectedQuote?.validFor || ''} placeholder="30 days" required />
              </label>

              <div className="drawer-actions">
                <button type="submit" className="drawer-save-btn">Save</button>
                <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Cancel</button>
              </div>
            </form>
          </>
        )}

        {drawerMode === 'detail' && selectedQuote && (
          <>
            <div className="drawer-detail-header">
              <div className="drawer-detail-avatar">{getInitials(selectedQuote.template)}</div>
              <div className="drawer-detail-title-group">
                <span className="drawer-eyebrow">Template</span>
                <h2 className="drawer-title">{selectedQuote.template}</h2>
                <span className={`status-pill ${selectedQuote.status === 'Active' ? 'success' : 'warning'}`} style={{ marginTop: '6px', display: 'inline-flex' }}>
                  <span className="dot" />
                  {selectedQuote.status}
                </span>
              </div>
              <button type="button" className="drawer-close-btn" onClick={closeDrawer} aria-label="Close">
                ✕
              </button>
            </div>

            <div className="drawer-divider" />

            <div className="drawer-stats-row">
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedQuote.plan}</span>
                <span className="drawer-stat-label">Plan</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedQuote.validFor}</span>
                <span className="drawer-stat-label">Valid</span>
              </div>
              <div className="drawer-stat-divider" />
              <div className="drawer-stat">
                <span className="drawer-stat-value">{selectedQuote.lines}</span>
                <span className="drawer-stat-label">Lines</span>
              </div>
            </div>

            <div className="drawer-divider" />

            <div className="drawer-detail-body">
              <div className="drawer-detail-section-label">Template details</div>

              <div className="drawer-detail-grid">
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Template</span>
                  <span className="drawer-detail-val">{selectedQuote.template}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Plan</span>
                  <span className="drawer-detail-val">{selectedQuote.plan}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Lines</span>
                  <span className="drawer-detail-val">{selectedQuote.lines}</span>
                </div>
                <div className="drawer-detail-item">
                  <span className="drawer-detail-key">Valid for</span>
                  <span className="drawer-detail-val">{selectedQuote.validFor}</span>
                </div>
              </div>
            </div>

            <div className="drawer-actions" style={{ marginTop: 'auto' }}>
              <button type="button" className="drawer-save-btn" onClick={() => setDrawerMode('create')}>Edit template</button>
              <button type="button" className="drawer-cancel-btn" onClick={closeDrawer}>Close</button>
            </div>
          </>
        )}
      </aside>

      <div className="customers-layout">
        <div className="customers-list-panel">
          <div className="table-toolbar">
            <div className="search-box">Search quotations...</div>
            <div className="filter-select">All statuses ⌄</div>
          </div>

          <div className="data-card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Template</th>
                  <th>Plan</th>
                  <th>Lines</th>
                  <th>Valid for</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {quotationRows.map((quote) => (
                  <tr
                    key={quote.id}
                    className={`customer-row ${selectedQuote?.id === quote.id && drawerMode === 'detail' ? 'customer-row--active' : ''}`}
                    onClick={() => openDetail(quote)}
                  >
                    <td className="customer-name">{quote.template}</td>
                    <td>{quote.plan}</td>
                    <td>{quote.lines}</td>
                    <td>{quote.validFor}</td>
                    <td>
                      <span className={`status-pill ${quote.status === 'Active' ? 'success' : 'warning'}`}>
                        <span className="dot" />
                        {quote.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="table-footer">Showing 3 of 3 records</div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
