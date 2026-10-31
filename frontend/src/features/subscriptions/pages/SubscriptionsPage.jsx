import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';

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
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [isCreateOpen, setCreateOpen] = useState(false);
  const visibleSubscriptions = useMemo(() => subscriptions.filter((item) => (
    `${item.number} ${item.customer} ${item.plan}`.toLowerCase().includes(query.toLowerCase())
    && (status === 'All statuses' || item.status === status)
  )), [query, status]);

  return (
    <AppShell
      title="Subscriptions"
      description="Every subscription and where it stands."
      breadcrumb="Brightloop / Subscriptions"
      activeNav="Subscriptions"
      primaryAction={<button className="primary-action" type="button" onClick={() => setCreateOpen(true)}>+ New subscription</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
      <div className="table-toolbar">
        <input className="table-search" type="search" placeholder="Search subscriptions..." aria-label="Search subscriptions" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select className="table-filter" aria-label="Filter subscriptions by status" value={status} onChange={(event) => setStatus(event.target.value)}><option>All statuses</option><option>Active</option><option>Confirmed</option><option>Quotation</option><option>Closed</option></select>
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
            {visibleSubscriptions.map((item) => (
              <tr key={item.number}>
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

        <div className="table-footer">Showing {visibleSubscriptions.length} of {subscriptions.length} records</div>
      </div>
      <Drawer title="New subscription" isOpen={isCreateOpen} onClose={() => setCreateOpen(false)} className="form-drawer"><form className="drawer-form" onSubmit={(event) => { event.preventDefault(); setCreateOpen(false); }}><label>Customer<select defaultValue="Northwind Traders"><option>Northwind Traders</option><option>Kerala Foods Co.</option><option>Tidewater Logistics</option><option>Lumen Clinics</option></select></label><label>Plan<select defaultValue="Business Monthly"><option>Business Monthly</option><option>Scale Annual</option><option>Secure Weekly</option><option>Starter Monthly</option></select></label><label>Start date<input type="date" /></label><label>Payment terms<select defaultValue="Immediate"><option>Immediate</option><option>Net 15</option><option>Net 30</option></select></label><button className="primary-action drawer-submit" type="submit">Save</button></form></Drawer>
    </AppShell>
  );
}
