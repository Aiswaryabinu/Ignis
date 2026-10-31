import { AppShell } from '../../../components/layout/AppShell.jsx';

const customers = [
  {
    name: 'Northwind Traders',
    email: 'ops@northwind.in',
    industry: 'Retail',
    subscriptions: 2,
    status: 'Active',
  },
  {
    name: 'Kerala Foods Co.',
    email: 'it@keralafoods.in',
    industry: 'Food & Beverage',
    subscriptions: 1,
    status: 'Active',
  },
  {
    name: 'Tidewater Logistics',
    email: 'admin@tidewater.in',
    industry: 'Logistics',
    subscriptions: 1,
    status: 'Active',
  },
  {
    name: 'Lumen Clinics',
    email: 'billing@lumen.in',
    industry: 'Healthcare',
    subscriptions: 0,
    status: 'Inactive',
  },
];

export function CustomersPage() {
  return (
    <AppShell
      title="Customers"
      description="People and companies you bill."
      breadcrumb="Brightloop / Customers"
      activeNav="customers"
      primaryAction={<button className="primary-action">+ Create</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
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

        <div className="table-footer">Showing 4 of 4 records</div>
      </div>
    </AppShell>
  );
}
