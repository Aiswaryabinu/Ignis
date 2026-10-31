import { AppShell } from '../../../components/layout/AppShell.jsx';

const subscriptions = [
  {
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

export function SubscriptionsPage() {
  return (
    <AppShell
      title="Subscriptions"
      description="Every subscription and where it stands."
      breadcrumb="Brightloop / Subscriptions"
      activeNav="Subscriptions"
      primaryAction={<button className="primary-action">+ New subscription</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
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

        <div className="table-footer">Showing 5 of 5 records</div>
      </div>
    </AppShell>
  );
}
