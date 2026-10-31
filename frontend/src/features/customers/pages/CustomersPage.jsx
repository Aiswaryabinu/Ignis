import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';

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
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [isCreateOpen, setCreateOpen] = useState(false);
  const visibleCustomers = useMemo(() => customers.filter((customer) => (
    `${customer.name} ${customer.email}`.toLowerCase().includes(query.toLowerCase())
    && (status === 'All statuses' || customer.status === status)
  )), [query, status]);

  return (
    <AppShell
      title="Customers"
      description="People and companies you bill."
      breadcrumb="Brightloop / Customers"
      activeNav="customers"
      primaryAction={<button className="primary-action" type="button" onClick={() => setCreateOpen(true)}>+ Create</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
      <div className="table-toolbar">
        <input className="table-search" type="search" placeholder="Search customers..." aria-label="Search customers" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select className="table-filter" aria-label="Filter customers by status" value={status} onChange={(event) => setStatus(event.target.value)}><option>All statuses</option><option>Active</option><option>Inactive</option></select>
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
            {visibleCustomers.map((customer) => (
              <tr key={customer.name}>
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

        <div className="table-footer">Showing {visibleCustomers.length} of {customers.length} records</div>
      </div>
      <Drawer title="Create" isOpen={isCreateOpen} onClose={() => setCreateOpen(false)} className="form-drawer"><form className="drawer-form" onSubmit={(event) => { event.preventDefault(); setCreateOpen(false); }}><label>Name<input required /></label><label>Email<input type="email" required /></label><label>Industry<input /></label><button className="primary-action drawer-submit" type="submit">Save</button></form></Drawer>
    </AppShell>
  );
}
