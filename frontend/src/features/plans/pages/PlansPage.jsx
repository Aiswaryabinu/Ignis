import { useMemo, useState } from 'react';

import { AppShell } from '../../../components/layout/AppShell.jsx';
import { Drawer } from '../../../components/ui/Drawer.jsx';

const plans = [
  {
    plan: 'Business Monthly',
    product: 'CloudDesk Pro',
    billing: 'Monthly',
    basePrice: '₹18,500',
    minQty: '5',
    renewal: 'Automatic',
    status: 'Active',
  },
  {
    plan: 'Scale Annual',
    product: 'Analytics Suite',
    billing: 'Yearly',
    basePrice: '₹2,16,000',
    minQty: '10',
    renewal: 'Automatic',
    status: 'Active',
  },
  {
    plan: 'Secure Weekly',
    product: 'SecureVault',
    billing: 'Weekly',
    basePrice: '₹2,800',
    minQty: '2',
    renewal: 'Manual',
    status: 'Draft',
  },
  {
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

export function PlansPage() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [isCreateOpen, setCreateOpen] = useState(false);
  const visiblePlans = useMemo(() => plans.filter((item) => (
    `${item.plan} ${item.product}`.toLowerCase().includes(query.toLowerCase())
    && (status === 'All statuses' || item.status === status)
  )), [query, status]);

  return (
    <AppShell
      title="Subscription Plans"
      description="Configure pricing, billing frequencies, and plan rules."
      breadcrumb="Brightloop / Subscription Plans"
      activeNav="Subscription Plans"
      primaryAction={<button className="primary-action" type="button" onClick={() => setCreateOpen(true)}>+ Create plan</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
      <div className="table-toolbar">
        <input className="table-search" type="search" placeholder="Search subscription plans..." aria-label="Search subscription plans" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select className="table-filter" aria-label="Filter subscription plans by status" value={status} onChange={(event) => setStatus(event.target.value)}><option>All statuses</option><option>Active</option><option>Draft</option></select>
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
            {visiblePlans.map((item) => (
              <tr key={item.plan}>
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

        <div className="table-footer">Showing {visiblePlans.length} of {plans.length} records</div>
      </div>
      <Drawer title="Create plan" isOpen={isCreateOpen} onClose={() => setCreateOpen(false)} className="form-drawer"><form className="drawer-form" onSubmit={(event) => { event.preventDefault(); setCreateOpen(false); }}><label>Plan name<input required /></label><label>Product<select defaultValue="CloudDesk Pro"><option>CloudDesk Pro</option><option>Analytics Suite</option><option>SecureVault</option></select></label><label>Billing<select defaultValue="Daily"><option>Daily</option><option>Weekly</option><option>Monthly</option><option>Yearly</option></select></label><label>Base price<input inputMode="decimal" /></label><label>Min. quantity<input inputMode="numeric" /></label><label>Renewal<select defaultValue="Automatic"><option>Automatic</option><option>Manual</option></select></label><button className="primary-action drawer-submit" type="submit">Save</button></form></Drawer>
    </AppShell>
  );
}
