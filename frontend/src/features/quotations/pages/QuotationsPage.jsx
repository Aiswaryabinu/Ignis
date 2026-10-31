import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';

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
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [isCreateOpen, setCreateOpen] = useState(false);
  const visibleQuotations = useMemo(() => quotations.filter((quote) => (
    `${quote.template} ${quote.plan}`.toLowerCase().includes(query.toLowerCase())
    && (status === 'All statuses' || quote.status === status)
  )), [query, status]);

  return (
    <AppShell
      title="Quotations"
      description="Start offers from a template with plan and product lines ready."
      breadcrumb="Brightloop / Quotations"
      activeNav="Quotations"
      primaryAction={<button className="primary-action" type="button" onClick={() => setCreateOpen(true)}>+ New template</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
      <div className="table-toolbar">
        <input className="table-search" type="search" placeholder="Search quotations..." aria-label="Search quotations" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select className="table-filter" aria-label="Filter quotations by status" value={status} onChange={(event) => setStatus(event.target.value)}><option>All statuses</option><option>Active</option><option>Draft</option></select>
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
            {visibleQuotations.map((quote) => (
              <tr key={quote.template}>
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

        <div className="table-footer">Showing {visibleQuotations.length} of {quotations.length} records</div>
      </div>
      <Drawer title="New template" isOpen={isCreateOpen} onClose={() => setCreateOpen(false)} className="form-drawer"><form className="drawer-form" onSubmit={(event) => { event.preventDefault(); setCreateOpen(false); }}><label>Template name<input required /></label><label>Plan<select defaultValue="Business Monthly"><option>Business Monthly</option><option>Scale Annual</option><option>Secure Weekly</option><option>Starter Monthly</option></select></label><label>Lines<input /></label><label>Valid for<input /></label><button className="primary-action drawer-submit" type="submit">Save</button></form></Drawer>
    </AppShell>
  );
}
