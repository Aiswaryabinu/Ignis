import { AppShell } from '../../../components/layout/AppShell.jsx';

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
  return (
    <AppShell
      title="Subscription Plans"
      description="Configure pricing, billing frequencies, and plan rules."
      breadcrumb="Brightloop / Subscription Plans"
      activeNav="Subscription Plans"
      primaryAction={<button className="primary-action">+ Create plan</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
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
            {plans.map((item) => (
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

        <div className="table-footer">Showing 4 of 4 records</div>
      </div>
    </AppShell>
  );
}
