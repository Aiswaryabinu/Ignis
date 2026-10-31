import { AppShell } from '../../../components/layout/AppShell.jsx';

const quotations = [
  {
    template: 'Retail Starter Pack',
    plan: 'Starter Monthly',
    lines: 'CloudDesk Pro × 5',
    validFor: '30 days',
    status: 'Active',
  },
  {
    template: 'Enterprise Analytics',
    plan: 'Scale Annual',
    lines: 'Analytics Suite × 10',
    validFor: '15 days',
    status: 'Active',
  },
  {
    template: 'Security Add-on',
    plan: 'Secure Weekly',
    lines: 'SecureVault × 2',
    validFor: '7 days',
    status: 'Draft',
  },
];

export function QuotationsPage() {
  return (
    <AppShell
      title="Quotations"
      description="Start offers from a template with plan and product lines ready."
      breadcrumb="Brightloop / Quotations"
      activeNav="Quotations"
      primaryAction={<button className="primary-action">+ New template</button>}
      secondaryAction={<button className="secondary-action">Export</button>}
    >
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
            {quotations.map((quote) => (
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

        <div className="table-footer">Showing 3 of 3 records</div>
      </div>
    </AppShell>
  );
}
